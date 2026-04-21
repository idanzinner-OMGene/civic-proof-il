# civic-api

FastAPI service for the civic-proof-il political verifier. Exposes health/readiness
endpoints in Phase 0; claim intake, retrieval, and verdict endpoints land in later phases.

## Endpoints

- `GET /healthz` — liveness probe. Always returns `{"status": "ok"}` while the process is alive.
- `GET /readyz` — readiness probe. Pings Postgres, Neo4j, OpenSearch, and MinIO and returns
  per-component booleans. Responds `503` if any dependency is unreachable.

## Configuration

All configuration is read from environment variables (no `.env` loading in the container).
See `src/api/settings.py` for the full list. Required variables:

| Group       | Variables |
|-------------|-----------|
| Postgres    | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| Neo4j       | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` |
| OpenSearch  | `OPENSEARCH_URL`, `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD` |
| MinIO       | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_ARCHIVE` |
| API         | `API_HOST`, `API_PORT`, `API_LOG_LEVEL`, `ENV` |

## Local development

From the repository root:

```bash
uv run --package civic-api uvicorn api.main:app --reload
```

Run the tests (no network dependencies — all pings are monkey-patched):

```bash
uv run --package civic-api pytest apps/api/tests
```

## Compose stack

In the Phase 0 docker-compose file the `api` service builds from `apps/api/Dockerfile`
and depends on `postgres`, `neo4j`, `opensearch`, and `minio`. The container healthcheck
curls `/healthz`; orchestration should wait for `/readyz` to be green before driving traffic.
