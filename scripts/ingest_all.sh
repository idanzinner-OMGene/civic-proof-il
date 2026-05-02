#!/usr/bin/env bash
# Run the full Knesset ingestion pipeline against live upstream sources.
#
# Usage:
#   bash scripts/ingest_all.sh [--dry-run] [--max-pages N] [--skip-index]
#
# Options:
#   --dry-run      Fetch + parse + normalize only; no Neo4j writes, no MinIO
#                  archival.  IngestRun rows are still written to Postgres.
#   --max-pages N  Cap OData pagination at N pages per adapter (useful for a
#                  quick smoke / integration test; omit for full crawl).
#   --skip-index   Do not run index_evidence.py after successful ingestion.
#
# Prerequisites:
#   make up        Docker Compose stack (Postgres, Neo4j, OpenSearch, MinIO)
#   make migrate   Alembic + Neo4j constraints + OpenSearch templates
#   .env           Must exist at repo root (see .env.example); vars are sourced
#                  automatically and container hostnames are remapped to localhost.
#
# The adapters are run in dependency order so that entity nodes exist before
# relationship adapters attempt to create edges against them.  The stub-MERGE
# pattern in the upsert templates provides resilience even out of order, but
# running in order ensures canonical attributes are fully populated first.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DRY_RUN=0
MAX_PAGES=""
SKIP_INDEX=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)    DRY_RUN=1; shift ;;
        --max-pages)  MAX_PAGES="$2"; shift 2 ;;
        --skip-index) SKIP_INDEX=1; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# Build shared adapter flags
ADAPTER_FLAGS=""
[[ $DRY_RUN -eq 1 ]]  && ADAPTER_FLAGS="${ADAPTER_FLAGS} --dry-run"
[[ -n "$MAX_PAGES" ]]  && ADAPTER_FLAGS="${ADAPTER_FLAGS} --max-pages ${MAX_PAGES}"

# ---------------------------------------------------------------------------
# Environment: source .env and remap container DNS → localhost for host runs
# ---------------------------------------------------------------------------
ENV_FILE="${REPO_ROOT}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: ${ENV_FILE} not found. Copy .env.example → .env and fill in credentials." >&2
    exit 1
fi

# shellcheck source=/dev/null
set -a; source "$ENV_FILE"; set +a

# When running from the host (outside Docker), the compose service names
# (postgres, neo4j, opensearch, minio) are not resolvable. Override to localhost
# so clients connect through the published ports.
export POSTGRES_HOST=localhost
export NEO4J_URI=bolt://localhost:7687
export OPENSEARCH_URL=http://localhost:9200
export MINIO_ENDPOINT=localhost:9000

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
echo "==> Checking prerequisites..."

check_service() {
    local name="$1"; local cmd="$2"
    if ! bash -c "$cmd" &>/dev/null; then
        echo "ERROR: ${name} is not reachable. Run \`make up\` and \`make migrate\` first." >&2
        exit 1
    fi
    echo "    [ok] ${name}"
}

check_service "Postgres"    "uv run python -c \"from civic_clients.postgres import ping; assert ping()\""
check_service "Neo4j"       "uv run python -c \"from civic_clients.neo4j import ping; assert ping()\""
check_service "MinIO"       "uv run python -c \"from civic_clients.minio_client import ensure_bucket; ensure_bucket()\""
check_service "OpenSearch"  "uv run python -c \"from civic_clients.opensearch import ping; assert ping()\""

# ---------------------------------------------------------------------------
# Helper: run one adapter with timing
# ---------------------------------------------------------------------------
run_adapter() {
    local name="$1"; local module="$2"; local package="$3"
    local start end elapsed

    echo ""
    echo "==> [$(date '+%H:%M:%S')] Starting adapter: ${name}"
    start=$(date +%s)

    # shellcheck disable=SC2086
    uv run --package "${package}" python -m "${module}" run ${ADAPTER_FLAGS}

    end=$(date +%s)
    elapsed=$(( end - start ))
    echo "    [done] ${name} — ${elapsed}s"
}

# ---------------------------------------------------------------------------
# Mode banner
# ---------------------------------------------------------------------------
echo ""
if [[ $DRY_RUN -eq 1 ]]; then
    echo "MODE: dry-run (fetch + parse + normalize; no Neo4j writes, no archival)"
else
    echo "MODE: full ingest (fetch + parse + normalize + Neo4j upsert + archival)"
fi
[[ -n "$MAX_PAGES" ]] && echo "MAX PAGES: ${MAX_PAGES} per OData adapter"
echo ""

TOTAL_START=$(date +%s)

# ---------------------------------------------------------------------------
# Adapter execution — dependency order
#
# 1. people            → creates Person nodes (dimension table, full history)
# 2. positions         → creates Party + Office; MEMBER_OF + HELD_OFFICE edges
# 3. committees        → creates Committee nodes (Knesset 25)
# 4. committee_memberships → MEMBER_OF_COMMITTEE edges (requires Person + Committee)
# 5. sponsorships      → creates Bill nodes (Knesset 25)
# 6. bill_initiators   → SPONSORED edges (requires Person + Bill)
# 7. votes             → VoteEvent nodes + CAST_VOTE edges
# 8. attendance        → AttendanceEvent nodes + ATTENDED edges
# ---------------------------------------------------------------------------
run_adapter "people"               "civic_ingest_people"               "civic-ingest-people"
run_adapter "positions"            "civic_ingest_positions"            "civic-ingest-positions"
run_adapter "committees"           "civic_ingest_committees"           "civic-ingest-committees"
run_adapter "committee_memberships" "civic_ingest_committee_memberships" "civic-ingest-committee-memberships"
run_adapter "sponsorships"         "civic_ingest_sponsorships"         "civic-ingest-sponsorships"
run_adapter "bill_initiators"      "civic_ingest_bill_initiators"      "civic-ingest-bill-initiators"
run_adapter "votes"                "civic_ingest_votes"                "civic-ingest-votes"
run_adapter "attendance"           "civic_ingest_attendance"           "civic-ingest-attendance"

# ---------------------------------------------------------------------------
# Post-ingest: index SourceDocument nodes into OpenSearch evidence_spans
# ---------------------------------------------------------------------------
if [[ $SKIP_INDEX -eq 1 ]]; then
    echo ""
    echo "==> Skipping evidence indexing (--skip-index)"
elif [[ $DRY_RUN -eq 1 ]]; then
    echo ""
    echo "==> Skipping evidence indexing (dry-run mode)"
else
    echo ""
    echo "==> [$(date '+%H:%M:%S')] Indexing evidence_spans in OpenSearch..."
    idx_start=$(date +%s)
    uv run python scripts/index_evidence.py
    idx_end=$(date +%s)
    echo "    [done] index-evidence — $(( idx_end - idx_start ))s"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$(( TOTAL_END - TOTAL_START ))
echo ""
echo "==> Ingestion complete — total elapsed: ${TOTAL_ELAPSED}s"
