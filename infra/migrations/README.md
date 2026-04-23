# Alembic migrations — `infra/migrations/`

PostgreSQL schema for `civic-proof-il` is managed by [Alembic](https://alembic.sqlalchemy.org/).
The `migrator` docker-compose one-shot service (see `apps/migrator`) runs
`alembic upgrade head` on startup, so every fresh `make up` yields a fully
migrated database before `api` and `worker` gate on `service_completed_successfully`.

## Layout

- `alembic.ini` — Alembic configuration. **`sqlalchemy.url` is intentionally
  blank**; the URL is composed in `env.py` from environment variables (see
  below). Do not hardcode credentials in `alembic.ini`.
- `env.py` — builds the SQLAlchemy URL from env vars, configures the Alembic
  context, and supports both offline (`--sql`) and online modes.
- `script.py.mako` — template used when generating a new revision.
- `versions/` — one file per migration, numeric prefix + description.

## Migration history

| Revision | File | Purpose |
|----------|------|---------|
| `0001`   | `versions/0001_init.py` | **Phase-0 placeholder.** Creates `schema_migrations_info`, a one-row bookkeeping table. No domain schema. |
| `0002`   | `versions/0002_phase1_domain_schema.py` | **Phase-1 domain schema.** Creates the nine pipeline tables (`ingest_runs`, `raw_fetch_objects`, `parse_jobs`, `normalized_records`, `entity_candidates`, `review_tasks`, `review_actions`, `verification_runs`, `verdict_exports`) per plan lines 232-241, plus supporting indexes. |

> `0001` stays in place as a historical anchor — do not edit it. Phase-1 domain
> schema starts at `0002`.

## Database URL

`env.py` composes the URL at runtime from these environment variables (see
`.env.example` for the canonical defaults):

- `POSTGRES_USER` (required)
- `POSTGRES_PASSWORD` (required)
- `POSTGRES_DB` (required)
- `POSTGRES_HOST` (default `postgres`, which is the docker-compose service name)
- `POSTGRES_PORT` (default `5432`)

Resulting URL: `postgresql+psycopg://<user>:<password>@<host>:<port>/<db>`.

Missing `POSTGRES_USER`, `POSTGRES_PASSWORD`, or `POSTGRES_DB` raises
`KeyError` on import — that is intentional: Alembic must never fall back to a
silent default.

## Running migrations

From the workspace root (host machine), with the Postgres container up:

```bash
# Upgrade to latest.
uv run alembic -c infra/migrations/alembic.ini upgrade head

# Downgrade one step.
uv run alembic -c infra/migrations/alembic.ini downgrade -1

# Render SQL without hitting the DB (useful for review / CI).
uv run alembic -c infra/migrations/alembic.ini --sql upgrade head
```

Inside the `migrator` container, `scripts/run-migrations.sh` wraps the same
commands (it also applies Neo4j constraints and OpenSearch index templates —
see the service's Dockerfile).

## Adding a new migration

1. Pick the next zero-padded four-digit number (`0003`, `0004`, …).
2. Generate the file:

   ```bash
   uv run alembic -c infra/migrations/alembic.ini revision -m "brief_description"
   ```

   Alembic will write `versions/<hash>_brief_description.py`. Rename it to
   follow our convention (see below) and set `revision`/`down_revision` to the
   zero-padded numeric strings, e.g. `revision = "0003"`,
   `down_revision = "0002"`. This keeps the history linear and easy to read.
3. Implement `upgrade()` and `downgrade()`. `downgrade()` must be the exact
   inverse (drop in reverse dependency order, drop indexes before their
   tables when the index is tracked by name).
4. Verify:

   ```bash
   # Syntax / importability.
   python -c "import ast; ast.parse(open('infra/migrations/versions/NNNN_foo.py').read())"

   # Offline SQL render (no DB required).
   POSTGRES_USER=x POSTGRES_PASSWORD=x POSTGRES_DB=x \
     uv run alembic -c infra/migrations/alembic.ini --sql upgrade head

   # Full round-trip against a live DB.
   uv run alembic -c infra/migrations/alembic.ini upgrade head
   uv run alembic -c infra/migrations/alembic.ini downgrade -1
   uv run alembic -c infra/migrations/alembic.ini upgrade head
   ```

## Naming convention for version files

`NNNN_brief_description.py`, where:

- `NNNN` — zero-padded, monotonically increasing integer. The same value is
  used for the `revision` variable inside the file (as a string).
- `brief_description` — snake_case, no more than ~5 words, describes the
  schema change (e.g. `phase1_domain_schema`, `add_people_index`,
  `drop_unused_staging_tables`).

Do not rename or renumber existing files once they land on `main` — Alembic's
`down_revision` links are keyed on the string value, and renumbering breaks
every downstream environment.

## Conventions baked into the schema

These are the shared contracts for Phase 1 and beyond (see the phase plan
"Shared cross-agent contracts" section):

- **Business keys are UUIDs**, stored with `postgresql.UUID(as_uuid=True)`.
  Every domain table has a surrogate `id BIGINT IDENTITY` primary key plus a
  `<entity>_id UUID UNIQUE NOT NULL` business key.
- **Timestamps are `TIMESTAMPTZ`** (`sa.TIMESTAMP(timezone=True)`), default
  `now()` where it makes sense (`started_at`, `captured_at`, `created_at`,
  `exported_at`).
- **Source tier is an integer with a CHECK constraint** — `source_tier IN (1, 2, 3)`.
  The same enum is enforced in JSON Schemas, OpenSearch mappings, and Neo4j.
- **Status / kind / action columns use `TEXT` plus a CHECK constraint** rather
  than native Postgres enums. This keeps migrations cheap (CHECK constraints
  are drop+add, Postgres enums are not).
- **JSON payloads use `JSONB`** (`postgresql.JSONB`), default `'{}'::jsonb`
  where the column is optional-but-non-null.
- **Foreign keys use `ON DELETE CASCADE`** along the pipeline flow
  (`ingest_runs → raw_fetch_objects → parse_jobs → normalized_records`,
  `review_tasks → review_actions`, `verification_runs → verdict_exports`).
  Deleting a root ingest run cleanly deletes everything derived from it.
