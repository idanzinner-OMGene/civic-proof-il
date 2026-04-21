#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/app}"
if [ ! -d "$ROOT_DIR/infra" ]; then
  # running on host (not in migrator container)
  ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi

echo "run-migrations: using ROOT_DIR=$ROOT_DIR"

: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

: "${NEO4J_URI:=bolt://neo4j:7687}"
: "${NEO4J_USER:?NEO4J_USER is required}"
: "${NEO4J_PASSWORD:?NEO4J_PASSWORD is required}"

: "${OPENSEARCH_URL:=http://opensearch:9200}"

echo "[1/3] Alembic upgrade head"
cd "$ROOT_DIR/infra/migrations"
alembic upgrade head

echo "[2/3] Applying Neo4j constraints"
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" --fail-at-end < "$ROOT_DIR/infra/neo4j/constraints.cypher"

echo "[3/3] Uploading OpenSearch index templates"
for tpl in "$ROOT_DIR"/infra/opensearch/templates/*.json; do
  [ -e "$tpl" ] || continue
  name="$(basename "$tpl" .json)"
  echo "  -> $name"
  curl -fsS -X PUT "$OPENSEARCH_URL/_index_template/$name" \
    -H 'Content-Type: application/json' \
    --data-binary "@$tpl"
  echo
done

echo "run-migrations: done"
