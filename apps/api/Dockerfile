FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

COPY pyproject.toml uv.lock ./
COPY apps/api       apps/api
COPY apps/worker    apps/worker
COPY apps/migrator  apps/migrator
COPY packages/common   packages/common
COPY packages/clients  packages/clients
COPY packages/ontology packages/ontology
COPY packages/prompts  packages/prompts
COPY services/archival                         services/archival
COPY services/ingestion/_common                services/ingestion/_common
COPY services/ingestion/knesset/people         services/ingestion/knesset/people
COPY services/ingestion/knesset/committees     services/ingestion/knesset/committees
COPY services/ingestion/knesset/votes          services/ingestion/knesset/votes
COPY services/ingestion/knesset/sponsorships   services/ingestion/knesset/sponsorships
COPY services/ingestion/knesset/attendance     services/ingestion/knesset/attendance
COPY services/ingestion/knesset/positions      services/ingestion/knesset/positions
COPY services/ingestion/knesset/bill_initiators services/ingestion/knesset/bill_initiators
COPY services/ingestion/knesset/committee_memberships services/ingestion/knesset/committee_memberships
COPY services/entity_resolution                services/entity_resolution
COPY services/claim_decomposition              services/claim_decomposition
COPY services/normalization                    services/normalization
COPY services/retrieval                        services/retrieval
COPY services/verification                     services/verification
COPY services/review                           services/review

RUN uv sync --package civic-api --frozen --no-dev

ENV API_HOST=0.0.0.0 API_PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=15s \
  CMD curl -sf http://localhost:${API_PORT}/healthz || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
