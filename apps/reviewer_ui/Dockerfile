FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv PATH="/app/.venv/bin:${PATH}"

COPY pyproject.toml uv.lock ./
COPY apps/reviewer_ui apps/reviewer_ui
COPY packages/common packages/common
RUN uv sync --package civic-reviewer-ui --frozen --no-dev

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD true
CMD ["uvicorn", "reviewer_ui.main:app", "--host", "0.0.0.0", "--port", "8001"]
