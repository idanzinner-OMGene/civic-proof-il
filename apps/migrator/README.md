# civic-migrator

One-shot migrator image. Applies Postgres Alembic migrations, Neo4j constraints, and OpenSearch index templates. Invoked by the `migrator` compose service (dependency for `api` and `worker`) and by `make migrate`.

## What it does

On container start, `scripts/run-migrations.sh` runs three steps in order:

1. **Postgres** — `alembic upgrade head` against `infra/migrations/`.
2. **Neo4j** — pipes `infra/neo4j/constraints.cypher` into `cypher-shell` (all statements use `IF NOT EXISTS`).
3. **OpenSearch** — `PUT`s every `infra/opensearch/templates/*.json` as an index template.

The script is idempotent and safe to re-run.

## Environment variables

Shared contract with the rest of the stack (see `.env.example`):

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `OPENSEARCH_URL`, `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`

## Running

Inside compose:

```bash
docker compose -f infra/docker/docker-compose.yml up migrator
```

From the host (without Docker), assuming services are reachable on localhost:

```bash
./scripts/run-migrations.sh
```

## Image contents

- `python:3.12-slim` base with `cypher-shell` 5.23 and `openjdk-17-jre-headless` installed.
- `uv`-installed Python deps: `alembic`, `psycopg[binary]`, `sqlalchemy`.
- Bundled repo content under `/app`: `infra/migrations/`, `infra/neo4j/constraints.cypher`, `infra/opensearch/templates/`, `scripts/run-migrations.sh`.
