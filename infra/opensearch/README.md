# OpenSearch — index templates

OpenSearch index templates. Full mappings arrive in Phase 1. Templates
placed under `templates/` here are uploaded by the migrator via
`scripts/run-migrations.sh` during `make up` / `make migrate`.

## Layout

- `templates/*.json` — one JSON file per index template (Agent F owns).
- `templates/.gitkeep` — keeps the directory tracked while empty.

Any `*.json` file in `templates/` will be PUT to
`$OPENSEARCH_URL/_index_template/<filename-without-extension>` by the
migrator.
