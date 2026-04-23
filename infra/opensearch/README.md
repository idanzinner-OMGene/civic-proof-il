# OpenSearch — index templates

OpenSearch index templates for the civic-proof-il canonical data model (Phase 1).
The migrator uploads every `*.json` in `templates/` via `scripts/run-migrations.sh`
during `make up` / `make migrate`. The filename (without `.json`) becomes the
index-template name: each file is PUT to
`$OPENSEARCH_URL/_index_template/<basename>`.

## Layout

- `templates/*.json` — one JSON file per index template (Phase-1 contract).

## Templates

| File | Template name | Index pattern | Priority | Purpose |
|------|---------------|---------------|----------|---------|
| `templates/0001_source_documents.json` | `0001_source_documents` | `source_documents*` | 100 | Archived source documents (title/body full-text, metadata) |
| `templates/0002_evidence_spans.json`   | `0002_evidence_spans`   | `evidence_spans*`   | 110 | Text spans from source documents used as evidence for claims |
| `templates/0003_claim_cache.json`      | `0003_claim_cache`      | `claim_cache*`      | 120 | Searchable cache of `AtomicClaim`s for reviewer UI + retrieval |

Patterns are disjoint, but priorities are explicit (higher wins on overlap) so
the gradient stays predictable if patterns are widened later.

## Reindex strategy

- **Template-first.** Index templates are uploaded before any index is created.
  New indexes that match a pattern inherit the mapping on creation — no per-index
  mapping needed.
- **Rollover / reindex later.** When a mapping needs to evolve (new field, type
  change) we bump the template (e.g. `0002_evidence_spans_v2.json`), create the
  next-generation index (e.g. `evidence_spans-000002`), and reindex from the
  previous generation. Alias cut-over happens on a rollover boundary. This
  convention is intentionally not implemented in Phase 1 — there are no live
  indexes yet — but the numeric filename prefixes make it easy to introduce.

## Hebrew analyzer — TODO

OpenSearch 2 does not ship a built-in `hebrew` analyzer. Every template declares
a named analyzer `text_he` and currently aliases it to the built-in `standard`
analyzer. All Hebrew-bearing text fields (`title`, `body`, `text`, `raw_text`,
`normalized_text`) reference `text_he` so the swap is a one-line change in each
template once we pick a real analyzer (either a custom analyzer built from
lowercase + ICU filters + a Hebrew stemmer, or a plugin such as `analysis-hebrew`).
This TODO is owned by Phase 2 / Phase 6 — tracked in the per-template `_meta`.

## Dev vs prod

- `number_of_shards: 1`, `number_of_replicas: 0` — dev only. Production must
  override via a component template or per-index settings.
- Security plugin is disabled in dev (`DISABLE_SECURITY_PLUGIN=true` in
  `docker-compose.yml`); prod will re-enable it and require TLS + auth.

## Strict mappings — warning

All three templates set `"dynamic": "strict"`. Writes with fields that are not
declared in the mapping will be rejected. **New fields require a template bump**
(edit the JSON, re-run `make migrate`, and reindex if the template change needs
to apply to existing indexes).
