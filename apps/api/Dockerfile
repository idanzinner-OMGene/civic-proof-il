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
COPY apps/api/pyproject.toml       apps/api/pyproject.toml
COPY apps/worker/pyproject.toml    apps/worker/pyproject.toml
COPY apps/migrator/pyproject.toml  apps/migrator/pyproject.toml
COPY packages/common/pyproject.toml    packages/common/pyproject.toml
COPY packages/clients/pyproject.toml   packages/clients/pyproject.toml
COPY packages/ontology/pyproject.toml  packages/ontology/pyproject.toml
COPY packages/prompts/pyproject.toml   packages/prompts/pyproject.toml

RUN uv sync --package civic-api --frozen --no-dev --no-install-project

COPY packages/common  packages/common
COPY packages/clients packages/clients
COPY apps/api         apps/api

RUN uv sync --package civic-api --frozen --no-dev

ENV API_HOST=0.0.0.0 API_PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=15s \
  CMD curl -sf http://localhost:${API_PORT}/healthz || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
