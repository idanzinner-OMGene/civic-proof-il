FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY apps/api/pyproject.toml ./
RUN uv pip install --system --no-cache \
    fastapi "uvicorn[standard]" pydantic pydantic-settings "psycopg[binary]" neo4j opensearch-py minio httpx
COPY apps/api/src /app/src
ENV PYTHONPATH=/app/src API_HOST=0.0.0.0 API_PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=15s CMD curl -sf http://localhost:${API_PORT}/healthz || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
