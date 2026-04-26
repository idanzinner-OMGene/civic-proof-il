# Agent Guide — civic-proof-il Political Verifier

> **Purpose:** Cross-session knowledge: architecture decisions, pitfalls, and invariants. For **what is done / next**, read [`PROJECT_STATUS.md`](PROJECT_STATUS.md). For **milestone-by-milestone implementation detail**, read [`CHANGELOG.md`](CHANGELOG.md).

---

## Architecture decisions (consolidated)

### Verification posture and LLM boundaries

- **Conservative abstention by default.** A verdict requires at least one Tier 1 source. Tier 1 conflicts go to human review. No verdict without archived provenance.
- **LLM role is strictly limited.** LLMs may assist claim decomposition, temporal normalization, evidence summarization, and reviewer explanations. They must **not** promote canonical facts, resolve conflicts between official records, or write directly to databases.
- **Deterministic / rule-first.** Rules before LLM in decomposition and entity resolution. Verdict engine is rule-driven in v1; LLMs summarize evidence only.
- **Source tiers** — Tier 1: official Knesset, gov.il role pages, government decisions, official elections. Tier 2: contextual official material. Tier 3: discovery-only (media, watchdogs, mirrors). See [political_verifier_v_1_plan.md](political_verifier_v_1_plan.md).

### Stack and services

- **uv + Python 3.12** — single toolchain; workspace in root [`pyproject.toml`](../pyproject.toml) `[tool.uv.workspace]`.
- **Neo4j Community + APOC** — graph facts. Auth env is `NEO4J_AUTH=<user>/<password>` (compose builds this from named vars).
- **Postgres** — pipelines only (`ingest_runs`, `raw_fetch_objects`, …), not domain facts. Domain entities live in Neo4j.
- **OpenSearch** — cache / search index only (`source_documents`, `evidence_spans`, `claim_cache`); strict dynamic mapping in dev.
- **MinIO** — immutable content-addressed archive; bucket from `MINIO_BUCKET_ARCHIVE`.
- **Migrator** — one-shot compose service: Alembic → `constraints.cypher` → OpenSearch index templates. API and worker wait on successful migrator.
- **Health** — `/healthz` = liveness; `/readyz` = readiness with four component booleans.

### Data model and contracts

- **UUID business keys** — Postgres surrogate PK + UUID; Neo4j `MERGE` on UUID string; OpenSearch `_id` = same UUID; schemas use `"format": "uuid"`.
- **Hand-written JSON Schemas (Draft 2020-12) are canonical** — not `model_json_schema()` output. Drift CLI compares field sets to Pydantic. See [`docs/adr/0001-canonical-data-model.md`](adr/0001-canonical-data-model.md).
- **`AtomicClaim` nullable FKs** — keys like `speaker_person_id` must be **present** in JSON; value may be `null`. Pydantic: `UUID | None` **without** `= None` defaults (`extra="forbid"`).
- **Schema `$ref`** — relative paths under `data_contracts/jsonschemas/`; validators register both `$id` and relative paths.
- **`populate_by_name=True`** on ontology models for future alias compatibility.
- **`vote_value`** — JSON Schema enum includes literal `null` per plan.

### Settings and clients

- **`civic_common.settings.Settings`** — single env contract; `get_settings()` is `@lru_cache` — call `get_settings.cache_clear()` when tests mutate env.
- **`apps/api/src/api/clients/*`** — thin re-exports over `civic_clients` so `health.py` monkeypatches (`ping_postgres`, …) keep working. Do not route health checks directly to `civic_clients` without updating tests.
- **`civic_clients.archive`** — `SOURCE_FAMILIES = {knesset, gov_il, elections}`; `build_archive_uri` reads bucket at call time; **`captured_at` must be timezone-aware**; `put_archive_object` asserts bucket match.

### Ingestion and graph (Phase 2+)

- **Real-data fixtures only** — see [`.cursor/rules/real-data-tests.mdc`](../.cursor/rules/real-data-tests.mdc) and [`docs/adr/0002-vcr-record-replay.md`](adr/0002-vcr-record-replay.md). Record via `make record-cassettes` / `python -m civic_archival fetch --out …`.
- **Postgres job queue** — `FOR UPDATE SKIP LOCKED`; no Redis/Celery for this envelope. [`docs/adr/0003-postgres-native-job-queue.md`](adr/0003-postgres-native-job-queue.md).
- **Deterministic IDs** — `uuid5(PHASE2_UUID_NAMESPACE, "knesset_<kind>:<external_id>")` with fixed namespace `00000000-0000-4000-8000-00000000beef` — **must never change** or all graph keys fork.
- **Archive + Postgres transaction** — `IngestRun` / `run_adapter` hold one Postgres transaction for archive rows; Neo4j upserts are separate commits.
- **Neo4j Community** — relationship property `IS NOT NULL` cannot be a graph constraint; enforced in Cypher upserts with `WHERE`.
- **`Person.external_ids` in Neo4j** — stored as **JSON string**, not a map property.

### Claims, retrieval, verdict (Phase 3–4)

- **Slot templates** — one per `ClaimType`; drift check ensures 1:1 with enum. [`docs/conventions/claim-slot-templates.md`](conventions/claim-slot-templates.md).
- **Decomposition** — rules-first + optional LLM behind `validate_slots`. [`docs/adr/0005-claim-decomposition-rules-first.md`](adr/0005-claim-decomposition-rules-first.md).
- **Temporal normalization** — deterministic; unknown → `granularity="unknown"`, no throw. [`docs/adr/0006-temporal-normalization-hebrew.md`](adr/0006-temporal-normalization-hebrew.md).
- **Entity resolution v2** — six-step ladder including rapidfuzz + optional LLM tiebreaker; polymorphic `entity_candidates` (migration `0005`). Fuzzy thresholds: `FUZZY_RESOLVE_THRESHOLD=92`, `FUZZY_MARGIN=5`.
- **Retrieval** — graph templates per claim type under `infra/neo4j/retrieval/`; lexical BM25 + optional kNN on `evidence_spans`. [`docs/adr/0007-deterministic-reranker.md`](adr/0007-deterministic-reranker.md).
- **Reranker `WEIGHTS`** — shared with verdict confidence rubric (single source of truth).
- **Verdict** — rule-only path in engine; thresholds `ABSTAIN_OVERALL=0.45`, `HUMAN_REVIEW_OVERALL=0.62` in code. [`docs/adr/0008-verdict-rubric-and-abstention.md`](adr/0008-verdict-rubric-and-abstention.md). Tier-2/3-only **contradicted** `vote_cast` → `needs_human_review=True`.
- **Provenance** — `EvidenceSummarizer` is the only LLM seam in verification; cannot change verdict fields.
- **Review actions** — vocabulary `approve|reject|relink|annotate|escalate` (Postgres CHECK) is **not** the same as verdict `status` values.

### Local Neo4j loader

- **`scripts/neo4j_load_phase1_local.py`** — intentionally standalone (reads `.cursor/.env`, raw driver). Do **not** refactor to `Settings` — keeps local browsing workflow decoupled from compose env.
- **Loader is destructive on re-run** — wipes then loads; unlike integration test cleanup which is automatic.

---

## Known pitfalls (by topic)

### Docker / Compose / images

- **Docker Desktop must be running** on macOS for `make up`.
- **`apps/api/Dockerfile`** — must use **`uv sync` against the full workspace**, not a flat `uv pip install` list — otherwise `civic_common` / `civic_clients` (and siblings) are missing at runtime.
- **Adding a workspace member** — extend `apps/api/Dockerfile` with `COPY` for that member’s tree; `uv sync --frozen` resolves **all** `[tool.uv.workspace].members`.
- **Migrator image** — pulls `cypher-shell` `.deb` from `dist.neo4j.org`; update URL if Neo4j major bumps.
- **Neo4j volume / `NEO4J_AUTH`** — password from first volume init only; change `.env` password → `docker compose down -v` or auth failures persist.
- **Ports 9000 / 9001** — Jupyter or other tools often bind these; blocks MinIO. Check with `lsof` before `make up`.

### Neo4j

- **Compose Neo4j vs local Neo4j** — both want host `7687`. Stop local (`brew services stop neo4j`) before `make up`; restart after `make down` if you use the local browser workflow.
- **`CALL { … } IN TRANSACTIONS`** — deprecation `01N00` in Neo4j 5; future fix may need `CALL () { … }` syntax.
- **Cypher `CALL { … } IN TRANSACTIONS` in loader** — still valid on current 5.x.

### Python / uv / packaging

- **`uv sync --all-packages`** after clone or when adding members — plain `uv sync` may not install every workspace package.
- **Do not add `__init__.py` under `packages/*/tests/` or `apps/*/tests/`** — causes `ImportPathMismatchError` / duplicate `tests` package with workspace-wide pytest.
- **Workspace member before `pyproject.toml` exists** — adding to `[tool.uv.workspace].members` first breaks every `uv` command until files exist; add pyproject + package together.
- **`packages/prompts`** — wheel needs `[tool.hatch.build.targets.wheel.force-include]` for YAML dirs or `load_card` breaks in installed env.

### Testing / pytest

- **`api.main` imports `Settings` at module load** — `apps/api/tests/conftest.py` and **`tests/integration/conftest.py`** must `setenv` / `setdefault` at **import** time, not only in fixtures.
- **`@pytest.mark.integration`** — registered in root `pyproject.toml`; keep it.
- **Unique `test_*.py` basenames** across adapters — e.g. use `test_people.py`, not duplicate `test_parse_normalize.py`.
- **Smoke `tests/smoke/conftest.py`** — supports `*_HOST` variants for host → published compose ports.
- **Integration tests on host** — `Settings` has `env_file=None`; export real credentials and point `POSTGRES_HOST`, `NEO4J_URI`, `OPENSEARCH_URL`, `MINIO_ENDPOINT` to **`localhost`** (not compose DNS names). Smoke has `*_HOST`; integration uses `civic_clients` → `Settings` directly.
- **`CIVIC_LIVE_WIRING=1` with `ENV=test`/`ci`** — required for API lifespan to mount real `GraphRetriever` / `LexicalRetriever` in integration tests; otherwise `VerifyPipeline` stays empty.
- **`!` in passwords** — zsh history expansion; use `bash -c 'export NEO4J_PASSWORD=…'` or careful quoting.

### Data / upstream / adapters

- **OData pagination** — accept both `odata.nextLink` (V3) and `@odata.nextLink` (V4).
- **`UPSERT_ROOT` / repo root** — from `services/ingestion/knesset/<adapter>/src/.../upsert.py` use **`parents[6]`**, not `[5]` (was a real bug).
- **Votes CSV** — official per-MK OData is bot-protected; oknesset mirror CSV is the realistic source.
- **`KNS_PersonToPosition.CommitteeID`** — always null in practice; use **`committee_memberships`** adapter (oknesset CSV) + `MkIndividualLookup`.
- **`KNS_BillInitiator`** — no `$filter=KnessetNum eq 25`; use `$orderby=BillInitiatorID desc&$top=100` for recordings.
- **`attended_mk_individual_ids`** — Python literal list string; parse with **`ast.literal_eval`**, not `json.loads`.
- **Attendance cassette** — need enough `--max-lines` so at least one row has non-empty attendee list (~51 lines).
- **`mk_individual_id` ≠ `PersonID`** — join only via `mk_individual.csv` dimension table; do not hard-code oknesset ids in tests.
- **New adapter checklist** — extend `AdapterKind`, `source_manifest.schema.json` `adapter` enum, `PHASE2_ADAPTERS` in `tests/smoke/test_alignment.py`, workspace `members`, Dockerfile `COPY`, manifests — Pydantic vs JSON Schema mismatch is **not** fully auto-guarded.
- **`raw_fetch_objects`** — dedupe by **`content_sha256`** globally; integration tests should assert hashes, not counts per `ingest_run_id`.
- **People manifest** — filtering `IsCurrent eq true` alone can miss historical MKs referenced by vote CSV; dimension table needs broad coverage for stub back-fill.
- **Stub `Person` from votes** — `source_tier=2` is provenance tier, not an identifier.

### API / FastAPI

- **`VerifyPipeline` in `Depends`** — use `Annotated[VerifyPipeline, Depends(get_pipeline)]`; avoid bare `Protocol` / optional types that break OpenAPI introspection.
- **Reviewer UI** — `Jinja2Templates.TemplateResponse(request, name, context)` (Starlette ≥0.37); wrong argument order breaks template resolution.
- **`record-statements.py --insecure-ssl`** — for MITM’d dev networks only; security judgment required on public Wi-Fi.

### OpenSearch / security plugin

- Dev compose disables security plugin but still sets `OPENSEARCH_INITIAL_ADMIN_PASSWORD` (2.12+ requirement).
- If security is re-enabled, upgrade weak dev passwords per OpenSearch policy.

### Alembic / migrations

- DB URL built in **`env.py`**, not `alembic.ini` (intentionally blank DSN in ini).
- **`schema_migrations_info`** — Phase-0 placeholder only; do not build domain on it.

---

## Conventions and ADRs (quick links)

### Conventions (`docs/conventions/`)

- [archive-paths.md](conventions/archive-paths.md)
- [source-manifests.md](conventions/source-manifests.md)
- [cassette-recording.md](conventions/cassette-recording.md)
- [claim-slot-templates.md](conventions/claim-slot-templates.md)
- [graph-retrieval-templates.md](conventions/graph-retrieval-templates.md)
- [prompt-cards.md](conventions/prompt-cards.md)

### ADRs (`docs/adr/`)

| ADR | Topic |
|-----|--------|
| [0001](adr/0001-canonical-data-model.md) | Canonical data model |
| [0002](adr/0002-vcr-record-replay.md) | VCR / real-data tests |
| [0003](adr/0003-postgres-native-job-queue.md) | Job queue |
| [0004](adr/0004-source-manifest-format.md) | Source manifests |
| [0005](adr/0005-claim-decomposition-rules-first.md) | Claim decomposition |
| [0006](adr/0006-temporal-normalization-hebrew.md) | Temporal normalization |
| [0007](adr/0007-deterministic-reranker.md) | Reranker |
| [0008](adr/0008-verdict-rubric-and-abstention.md) | Verdict / abstention |
| [0009](adr/0009-reviewer-ui-tech-stack.md) | Reviewer UI stack |
| [0010](adr/0010-conflict-detection-strategy.md) | Conflict detection |
| [0011](adr/0011-eval-harness-metrics.md) | Eval harness |

---

## Key invariants (do not break)

1. **`PHASE2_UUID_NAMESPACE` and `knesset_<kind>:` string formats** — stable forever for graph idempotency.
2. **Real upstream bytes in fixtures** — no synthetic domain payloads in `tests/fixtures/**` (policy + alignment scan).
3. **Hand-written schemas canonical** — drift check is structural, not byte-identical to generated JSON Schema.
4. **`captured_at` timezone-aware** anywhere it feeds archive URIs or `TIMESTAMPTZ`.
5. **Archive immutability** — one content hash → one URI; cross-bucket writes are bugs.
6. **Review `decision` vocabulary ≠ verdict `status` vocabulary** — different enums, different purposes.

---

## Performance and eval notes

- Offline `make eval` baselines and gate discussion live in [`PROJECT_STATUS.md`](PROJECT_STATUS.md) (**Performance baselines**). Refresh when wiring live retrieval or expanding semantic gold labels.

---

## For future agents

Append short, durable notes to the **Agent scratchpad** section in [`PROJECT_STATUS.md`](PROJECT_STATUS.md). If a note becomes evergreen (multi-session pitfall or policy), **promote it into this guide** in the right section and trim the scratchpad.
