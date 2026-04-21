# civic-worker

Placeholder worker that ticks on a timer. Phase 2+ will plug in a real job queue (Celery/arq/RQ TBD).

## What this is

A minimal background worker scaffold for the `civic-proof-il` political verifier. It:

- Loads configuration via `pydantic-settings` (Postgres + Neo4j credentials, `WORKER_TICK_SECONDS`, `ENV`).
- Runs a simple `run_forever` loop that invokes `run_once` on each tick and sleeps.
- Handles `SIGTERM` / `SIGINT` for graceful shutdown.

There is no real job queue wired up yet. Phase 2 ingestion and Phase 3 claim-pipeline tasks will decide whether we adopt Celery, arq, RQ, or another executor.

## Layout

```
apps/worker/
  pyproject.toml
  Dockerfile
  .dockerignore
  src/worker/__init__.py
  src/worker/main.py       # run_once + run_forever
  src/worker/settings.py   # pydantic-settings Settings + get_settings()
  tests/test_smoke.py
```

## Local development

```bash
cd apps/worker
uv sync  # or pip install -e .
pytest
```

The test suite sets the required env vars via monkeypatch and never touches the network.

## Running the worker

```bash
python -m worker.main
```

Required environment variables:

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

Optional:

- `WORKER_TICK_SECONDS` (default `30`)
- `ENV` (default `dev`)
