# Deployment Guide — civic-proof-il Political Verifier

> **Purpose:** Operator runbook for getting the system running locally or in production. For architecture context see [`ARCHITECTURE.md`](ARCHITECTURE.md). For known pitfalls see [`AGENT_GUIDE.md`](AGENT_GUIDE.md).

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker Desktop (or Docker Engine + Compose plugin) | ≥ 4.28 | Must be running before `make up` |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python | 3.12 | Managed by uv via `.python-version` |
| bash | ≥ 3.2 | Used by all shell scripts |
| make | GNU make | `brew install make` on macOS |

**macOS note:** Stop any local Neo4j Homebrew service before `make up` — both want port 7687.

```bash
brew services stop neo4j   # if installed
lsof -i :9000              # check MinIO port; Jupyter also uses 9000
```

---

## Quick start (local development)

```bash
# 1. Clone and configure
git clone <repo-url> civic-proof-il
cd civic-proof-il
cp .env.example .env        # edit .env to set REVIEWER_UI_PASSWORD and optionally change credentials

# 2. Install Python toolchain and workspace packages
make bootstrap              # copies .env if missing, runs uv sync --all-packages

# 3. Start all services
make up                     # builds images, starts Postgres / Neo4j / OpenSearch / MinIO / API / worker / reviewer_ui
                            # migrator runs automatically and exits; wait ~60s for Neo4j to fully start

# 4. Verify health
curl http://localhost:8000/healthz    # → {"status":"ok"}
curl http://localhost:8000/readyz     # → {"status":"ready","components":{...all true...}}

# 5. Load Knesset graph data (optional, ~90 min)
make ingest                 # populates Neo4j with 188K nodes and 1.7M relationships from live upstream

# 6. Index evidence in OpenSearch (run after ingest)
make index-evidence

# 7. Run benchmark
make eval                   # offline eval, exits 0 if all gates pass
```

The reviewer UI is available at http://localhost:8001 (credentials from `.env` `REVIEWER_UI_USER` / `REVIEWER_UI_PASSWORD`).

---

## Environment variable reference

All env vars are defined in `.env` (copied from `.env.example`). The `Settings` singleton in `packages/common/src/civic_common/settings.py` is the authoritative contract.

### Postgres

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `postgres` | Container hostname (use `localhost` for host-side scripts) |
| `POSTGRES_PORT` | `5432` | TCP port |
| `POSTGRES_USER` | `civic` | Database user |
| `POSTGRES_PASSWORD` | `civic_dev_pw` | Password — change in production |
| `POSTGRES_DB` | `civic` | Database name |

### Neo4j

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://neo4j:7687` | Bolt URI (use `bolt://localhost:7687` for host-side scripts) |
| `NEO4J_USER` | `neo4j` | Username |
| `NEO4J_PASSWORD` | `civic_dev_pw` | Password — change in production; must match volume-init value |

**Important:** Neo4j bakes the password into the volume on first start. If you change `NEO4J_PASSWORD` after data has been written, run `make down` (which removes volumes) before `make up`.

### OpenSearch

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSEARCH_URL` | `http://opensearch:9200` | HTTP endpoint (use `http://localhost:9200` for host-side scripts) |
| `OPENSEARCH_USER` | `admin` | Username (security plugin disabled in dev) |
| `OPENSEARCH_PASSWORD` | `admin` | Password |

### MinIO

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | `minio:9000` | Host:port (use `localhost:9000` for host-side scripts) |
| `MINIO_ACCESS_KEY` | `minioadmin` | Access key |
| `MINIO_SECRET_KEY` | `minioadmin` | Secret key — change in production |
| `MINIO_BUCKET_ARCHIVE` | `civic-archive` | Immutable archive bucket; created automatically on startup |

### API and reviewer UI

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `dev` | `dev` / `test` / `ci` / `prod` — controls log format and live-wiring guards |
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Bind port |
| `API_LOG_LEVEL` | `info` | uvicorn log level |
| `REVIEWER_UI_USER` | `reviewer` | HTTP Basic Auth username |
| `REVIEWER_UI_PASSWORD` | *(must be set)* | HTTP Basic Auth password — UI returns 503 if missing |
| `CIVIC_LIVE_WIRING` | *(unset)* | Set to `1` with `ENV=test`/`ci` to mount live graph + lexical retrievers in tests |

---

## Host-side scripts (overriding container DNS)

When running Python scripts (`scripts/eval.py`, `scripts/freshness_check.py`, etc.) directly on the host (not inside a container), you must point them at the published Docker ports:

```bash
export POSTGRES_HOST=localhost
export NEO4J_URI=bolt://localhost:7687
export OPENSEARCH_URL=http://localhost:9200
export MINIO_ENDPOINT=localhost:9000
```

`make eval-live` and `make freshness` already do this via a `bash -c 'source .env; ...'` wrapper.

---

## Key Makefile targets

| Target | Description |
|--------|-------------|
| `make up` | Build images and start all services (Postgres, Neo4j, OpenSearch, MinIO, API, worker, reviewer_ui) |
| `make down` | Stop stack and **remove volumes** (data wiped) |
| `make migrate` | Re-run Alembic + Neo4j constraints + OpenSearch templates against a running stack |
| `make test` | Run unit tests for apps/api and apps/worker only (subset of full suite) |
| `make smoke` | Run smoke tests (requires `make up`) |
| `make eval` | Offline Phase-6 benchmark — gates at min_rows=25, f1_verdict=1.0 |
| `make eval-live` | Live benchmark against running stack (requires ingest data) |
| `make ingest` | Full Knesset data ingest (~90 min, requires `make up`) |
| `make ingest-dry` | Fetch + parse only, no graph writes |
| `make index-evidence` | Index OpenSearch evidence spans from Neo4j SourceDocument nodes |
| `make freshness` | Emit adapter freshness report to `reports/freshness_check.json` |
| `make record-cassettes` | Re-record all Phase-2 test cassettes from live upstream (needs `full_network`) |
| `make fmt` | Format code with ruff |
| `make lint` | Lint code with ruff |

---

## Service ports (published to host)

| Service | Port | Notes |
|---------|------|-------|
| API | 8000 | FastAPI; `/healthz`, `/readyz`, `/claims/verify`, `/persons/{id}`, `/review/tasks` |
| Reviewer UI | 8001 | Jinja2 HTMX queue; HTTP Basic Auth required |
| Neo4j browser | 7474 | HTTP browser at http://localhost:7474 |
| Neo4j bolt | 7687 | Bolt protocol for drivers |
| Postgres | 5432 | Standard psql / psycopg |
| OpenSearch | 9200 | REST API |
| MinIO console | 9001 | Web console at http://localhost:9001 |
| MinIO API | 9000 | S3-compatible API |

---

## Full Knesset graph ingest

The ingest pipeline crawls Knesset OData + oknesset CSV mirrors and populates Neo4j with the complete historical record. It requires the stack to be running (`make up`).

```bash
make ingest          # full crawl; ~90 min; writes 188K nodes / 1.7M relationships
make ingest-dry      # dry run: fetch + parse only, no Neo4j writes
```

After ingest, index evidence spans for lexical retrieval:

```bash
make index-evidence
```

**Adapter order (managed automatically by `scripts/ingest_all.sh`):**

1. `people` — all MKs ever (KNS_Person)
2. `committees` — Knesset-25 committees
3. `positions` — MEMBER_OF + HELD_OFFICE edges (KNS_PersonToPosition)
4. `committee_memberships` — MEMBER_OF_COMMITTEE edges (oknesset CSV)
5. `sponsorships` — SPONSORED edges (KNS_Bill)
6. `bill_initiators` — SPONSORED edges for all initiators (KNS_BillInitiator)
7. `votes` — CAST_VOTE edges (oknesset CSV, ~1.27M edges)
8. `attendance` — ATTENDED edges (oknesset CSV)

---

## Backup and restore

### Neo4j

Neo4j data lives in the `neo4j_data` Docker volume. To back up:

```bash
# Backup: dump while stack is down
make down              # stop stack (removes volumes — DON'T use make down for backup!)
```

**Warning:** `make down` removes volumes. For a safe backup, stop Neo4j only and use `neo4j-admin database dump`:

```bash
docker compose stop neo4j
docker compose run --rm neo4j neo4j-admin database dump --to-path=/data neo4j
# copy the file from the volume before restarting
docker compose start neo4j
```

For full graph recovery, re-run `make ingest` (source data is canonical; re-ingesting from upstream is the primary recovery path).

### Postgres

Postgres stores only pipeline metadata (ingest runs, job queue, entity candidates, review tasks). It can be fully reconstructed by re-running migrations and re-ingesting.

```bash
# Manual dump (while stack is running)
docker compose exec postgres pg_dump -U civic civic > backup.sql

# Restore
docker compose exec -T postgres psql -U civic civic < backup.sql
```

### MinIO

MinIO holds immutable content-addressed archive objects. Back up the `civic-archive` bucket using the MinIO client (`mc`) or S3-compatible tooling. In production, consider enabling versioning or replication.

---

## Monitoring and freshness

### API health endpoints

- `GET /healthz` — liveness probe (no auth required; returns 200 if process is alive)
- `GET /readyz` — readiness probe with per-component status:
  ```json
  {"status": "ready", "components": {"postgres": true, "neo4j": true, "opensearch": true, "minio": true}}
  ```

### Manifest freshness

```bash
make freshness    # writes reports/freshness_check.json
```

Output includes `last_run_at`, `age_seconds`, and `stale` (boolean) per adapter, computed against twice the adapter's expected cadence. Requires a running Postgres (`make up`).

### Reviewer UI monitoring

The reviewer UI exposes `/healthz` (exempt from auth). Wire this into your load balancer or uptime monitor.

---

## Troubleshooting

### Stack fails to start

```bash
make logs       # tail all services
make ps         # check which services are unhealthy
```

Common causes:
- **Port conflict:** `lsof -i :7687` (Neo4j), `lsof -i :9000` (MinIO/Jupyter), `lsof -i :5432` (Postgres)
- **Volume corruption:** `make down && make up` (wipes data, rebuilds clean)
- **Migrator failed:** Check `docker compose logs migrator`; re-run `make migrate` after fixing

### `GET /readyz` returns false components

Each component boolean maps to a `ping()` call in `civic_clients`. If Neo4j is false, the bolt connection is timing out (check `neo4j_data` volume and `NEO4J_PASSWORD` match).

### Host-side tests fail with connection errors

Ensure host-side env vars point to `localhost` (not Docker DNS names). See [Host-side scripts](#host-side-scripts-overriding-container-dns).

### Live eval fails entity resolution

Run `make eval-live` via `bash` (not zsh) to avoid `!` history expansion on the password:
```bash
bash -c 'source .env; export POSTGRES_HOST=localhost NEO4J_URI=bolt://localhost:7687 OPENSEARCH_URL=http://localhost:9200 MINIO_ENDPOINT=localhost:9000; uv run python scripts/eval.py --live'
```

### Neo4j password auth failures after `.env` change

Neo4j bakes the password into its volume on first init. Changing `.env` after the volume exists causes auth failures. Fix:
```bash
docker compose down -v     # DESTRUCTIVE — wipes all volumes
make up
make ingest                # re-ingest from upstream
```

---

## Production deployment notes

This project targets local/on-premises deployment. For production:

1. **Secrets:** Replace all `_dev_pw` / `change_me_*` values in `.env` with strong secrets managed by a secrets manager (Vault, AWS Secrets Manager, etc.). Never commit real credentials.
2. **Neo4j:** Consider Neo4j Enterprise for relationship property constraints, clustering, and native backups.
3. **OpenSearch:** Increase `number_of_shards` and `number_of_replicas` in `infra/opensearch/templates/` (currently `1`/`0` for dev). Re-create indexes after template changes.
4. **MinIO:** Enable versioning and configure lifecycle policies for long-term archive retention.
5. **Reviewer UI auth:** The current HTTP Basic Auth (`REVIEWER_UI_PASSWORD`) is a v1 baseline. For production, integrate with an SSO provider or add session-based auth.
6. **Logging:** `ENV=prod` produces JSON-formatted structured logs. Route them to a log aggregator (Loki, Datadog, etc.).
7. **TLS:** Put a reverse proxy (nginx, Caddy) in front of the API and reviewer UI.
