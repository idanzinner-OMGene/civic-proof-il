#!/usr/bin/env bash
# Seed the live stack with a minimal representative dataset from recorded cassettes.
#
# Replays all eight Phase-2/2.5 adapters against tests/fixtures/phase2/cassettes/
# — no internet required.  Re-running is idempotent.
#
# Prerequisites: make up && make migrate
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_FILE="${REPO_ROOT}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: ${ENV_FILE} not found. Copy .env.example → .env and fill in credentials." >&2
    exit 1
fi

# shellcheck source=/dev/null
set -a; source "$ENV_FILE"; set +a

# Remap container DNS → localhost for host-side execution
export POSTGRES_HOST=localhost
export NEO4J_URI=bolt://localhost:7687
export OPENSEARCH_URL=http://localhost:9200
export MINIO_ENDPOINT=localhost:9000

cd "${REPO_ROOT}"
exec uv run python scripts/seed_demo.py
