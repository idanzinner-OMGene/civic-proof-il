# Reviewer UI (`civic-reviewer-ui`)

Phase 5: minimal HTML views over the main API’s `GET /review/tasks` and
per-task help text for the JSON `POST` bodies.

## Run (host)

```bash
export CIVIC_API_BASE=http://localhost:8000
uv run --package civic-reviewer-ui uvicorn reviewer_ui.main:app --port 8001
```

## Docker

The `reviewer_ui` service in `infra/docker/docker-compose.yml` sets
`CIVIC_API_BASE=http://api:8000` and publishes port 8001.

## Tests

`uv run --package civic-reviewer-ui pytest apps/reviewer_ui/tests`
