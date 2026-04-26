# Project Status — civic-proof-il Political Verifier

> Single source of truth for all agents and contributors. Update this file after every milestone or agent session.

---

## Completed milestones

### Repo hygiene (Phase -1) — 2026-04-21
- Initial repository setup for the political verifier v1.
- Added `.gitignore` covering secrets, OS files, and Python/Node/Docker artifacts.
- Added `README.md` with project description and links to plan and status doc.
- Pruned `.cursor/skills/` to only project-relevant skills (feynman-explainer, neo4j-upload-checks, plan-assist-agent, research-agent, spike-researcher, standalone-report). Removed OMGene/survey-specific skills.
- Kept all three `.cursor/rules/` files and `templates/adr-template.md`.
- Excluded `.cursor/.env` from version control (contains live credentials).
- Key artifact: `docs/political_verifier_v_1_plan.md` (full v1 spec, 8-week schedule, 20 Codex tickets).

### Phase 0 — Repo bootstrap — 2026-04-21
- Monorepo scaffold created to match `docs/political_verifier_v_1_plan.md` required structure (apps/, packages/, services/, infra/, data_contracts/, tests/, scripts/, docs/).
- docker-compose stack: Postgres 16, Neo4j 5 community (with APOC), OpenSearch 2, MinIO, plus a one-shot `migrator` service and `api` + `worker` service skeletons.
- `apps/api` (FastAPI) with `/healthz` and `/readyz` checking Postgres / Neo4j / OpenSearch / MinIO.
- `apps/worker` minimal tick loop stub (real job queue deferred to Phase 2).
- `apps/migrator` one-shot image that runs Alembic, applies Neo4j constraints, and uploads OpenSearch index templates.
- Alembic baseline migration `0001_init` creates `schema_migrations_info`.
- Placeholder Neo4j constraints for the Phase 1 node ID set (Person, Party, Office, Committee, Bill, SourceDocument, AtomicClaim, Verdict) — all `IF NOT EXISTS`.
- Placeholder OpenSearch index template `0001_sources_template` covering `source_documents`, `evidence_spans`, `claim_cache`.
- Root `Makefile` with `up`/`down`/`test`/`smoke`/`migrate`/`seed-demo`/`fmt`/`lint`/`clean`/`bootstrap`.
- Smoke tests under `tests/smoke/` cover stack health, direct client connectivity, migration artifacts, and a static alignment audit (`test_alignment.py` passes locally — 5/5 without the stack).
- Artifacts: `docs/ARCHITECTURE.md`, `CONTRIBUTING.md`, `.env.example`, `.editorconfig`, `.python-version`, `.tool-versions`.
- **Wave-2 audit (Agent G) — 2026-04-21**: Wrote the `tests/smoke/` suite; patched one drift (API test conftest didn't set env vars at module load — `api.main` instantiates `Settings()` at import time via `app = create_app()`, which pytest triggers during collection before per-test fixtures run). End-to-end `make up` validation deferred — local Docker Desktop daemon not running and `uv` not on PATH on this host; CI will cover first full stack validation.

### Phase 1 — Canonical data model (parallel bootstrap) — 2026-04-21
Plan: `/Users/idan/.cursor/plans/phase1-canonical-data-model_f446d718.plan.md`. Six parallel write lanes in Wave 1 (agents A–F) plus an audit lane in Wave 2 (agent G).

**Postgres (Agent A — `0002_phase1_domain_schema`)**
- Nine pipeline tables: `ingest_runs`, `raw_fetch_objects`, `parse_jobs`, `normalized_records`, `entity_candidates`, `review_tasks`, `review_actions`, `verification_runs`, `verdict_exports`.
- Four supporting indexes: `idx_raw_fetch_objects_archive_uri`, `idx_normalized_records_kind`, `idx_review_tasks_status_priority`, `idx_verification_runs_claim_id`.
- `downgrade()` drops everything in reverse order.
- Uses `sa.BigInteger() + sa.Identity(always=False)` for surrogate PKs (equivalent to `BIGSERIAL` in Postgres 10+; flagged by Agent G as spirit-compliant with the plan).
- `infra/migrations/README.md` documents the migration.

**Neo4j (Agent B — `constraints.cypher` rewrite + `upserts/` tree)**
- 24 constraints in `infra/neo4j/constraints.cypher`: 12 unique + 12 existence, one pair per domain node (Person, Party, Office, Committee, Bill, VoteEvent, AttendanceEvent, MembershipTerm, SourceDocument, EvidenceSpan, AtomicClaim, Verdict). All statements `IF NOT EXISTS`.
- 12 node upsert templates under `infra/neo4j/upserts/*.cypher` (one per node, each `MERGE` on the business key with `ON CREATE` / `ON MATCH SET`).
- 11 relationship templates under `infra/neo4j/upserts/relationships/*.cypher`: `about_bill`, `about_person`, `cast_vote`, `contradicted_by`, `evaluates`, `has_span`, `held_office`, `member_of`, `member_of_committee`, `sponsored`, `supported_by`.
- Relationship-property existence (e.g. `valid_from`) is enforced by `WHERE … IS NOT NULL` inside the upsert templates — Neo4j Community can't declare this at the constraint level. `infra/neo4j/README.md` spells out the convention.

**OpenSearch (Agent C — `infra/opensearch/templates/*`)**
- Replaced the Phase-0 placeholder with three strict-dynamic templates: `0001_source_documents.json`, `0002_evidence_spans.json`, `0003_claim_cache.json`.
- Priorities `100 / 110 / 120`; `number_of_shards: 1`, `number_of_replicas: 0` for dev (prod overrides documented in `infra/opensearch/README.md`).
- Hebrew text fields declare a named analyzer `text_he`, currently aliased to the built-in `standard` analyzer until a real Hebrew analyzer lands.

**Contracts (Agent D — `data_contracts/jsonschemas/` + `packages/ontology/`)**
- 15 hand-written Draft 2020-12 JSON Schemas (12 entity + 3 in `common/`: `source_tier`, `time_scope`, `confidence`). All entity schemas use `dynamic:"strict"`-compatible shapes and `$id = https://civic-proof-il.org/schemas/<name>.schema.json`.
- 13 Pydantic v2 models under `packages/ontology/src/civic_ontology/models/` (one per schema + `common.py` for shared types). Models use `ConfigDict(extra="forbid", populate_by_name=True)`.
- Drift-check CLI `python -m civic_ontology.schemas --check` verifies schema ↔ model alignment (`properties` keys and `required` lists); validates Draft 2020-12 metaschema. Hand-written schemas are canonical (chose the alternative to `model_json_schema()` auto-generation per rationale in the module docstring).
- 31 tests green (`test_roundtrip`, `test_fixtures_validate`, `test_schema_drift`).
- 12 Phase-1 fixtures under `tests/fixtures/phase1/*.json` with deterministic UUIDs `00000000-0000-4000-8000-00000000000N` for N=01..0c.

**Clients + archive convention (Agent E — `packages/clients/` + `docs/conventions/archive-paths.md`)**
- Promoted `Settings` to `packages/common/src/civic_common/settings.py`; `apps/api/src/api/settings.py` is a two-line re-export. Env-var contract has a single source of truth.
- New `packages/clients/` package: `archive.py` (`build_archive_uri`, `parse_archive_uri`, `content_sha256`, `SOURCE_FAMILIES`), `postgres.py` (sync + async + `ping`), `neo4j.py` (cached driver + `run_upsert(template_path, params)`), `opensearch.py` (client + `put_index_templates(root)`), `minio_client.py` (`ensure_bucket`, `put_archive_object` with bucket-mismatch guard).
- `apps/api/src/api/clients/*` refactored to re-export from `civic_clients` while preserving the `ping_postgres`/`ping_neo4j`/… names so `apps/api/tests/test_health.py` monkeypatches still work.
- `docs/conventions/archive-paths.md` formalises the URI scheme `s3://<bucket>/<source_family>/<YYYY>/<MM>/<DD>/<sha256>.<ext>`, SHA-256 content hashing, immutability rule, and the `SOURCE_FAMILIES = {knesset, gov_il, elections}` whitelist.
- 27 tests pass under `uv run pytest` (common/3 + clients/20 + api/4).
- Golden URI (sanity): `source_family="knesset"`, `captured_at=2024-01-15T09:00:00+00:00`, `content=b"hello"`, `extension="html"`, bucket `civic-archive` → `s3://civic-archive/knesset/2024/01/15/2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824.html`.

**Docs (Agent F)**
- New `docs/DATA_MODEL.md` with mermaid ERD of the nine Postgres tables, graph diagram of the 12 nodes + 11 relationships, OpenSearch index summary, cross-store ID mapping.
- New ADR `docs/adr/0001-canonical-data-model.md` recording the UUID4/Postgres-pipelines/Neo4j-facts/OpenSearch-cache/Draft-2020-12/Pydantic-v2 decisions.
- Appended Phase-1 section to `docs/ARCHITECTURE.md` without disturbing the Phase-0 section.

**Wave-2 acceptance + audit (Agent G) — 2026-04-21**
- Wrote `tests/integration/test_phase1_persistence.py` — end-to-end acceptance test (Pydantic validation → Postgres round-trip → Neo4j round-trip → OpenSearch round-trip → idempotency → cleanup). Marked `@pytest.mark.integration`, skips the whole module if any of the four backing stores is unreachable. `ast.parse` clean.
- Extended `tests/smoke/test_migrations.py` with Phase-1 table/constraint/template coverage (9 Postgres tables, 24 Neo4j constraints — 12 unique + 12 existence — and the three OpenSearch index templates). Removed the now-stale `test_opensearch_template_registered` check for the deleted `0001_sources_template.json` placeholder.
- Extended `tests/smoke/test_alignment.py` with 89 Phase-1 parametrized static checks covering the migration file, constraints, upsert templates (nodes + relationships), OpenSearch templates, JSON Schemas + `common/` refs, Pydantic models, docs, and the `civic_clients.archive` surface. All 94 tests green (`uv run pytest tests/smoke/test_alignment.py`).
- Drift patches applied (see "Drift patches" below).
- End-to-end `make up && make smoke` validation deferred at this audit — superseded by the live-validation run on 2026-04-22 (see next entry).

**Live validation — 2026-04-22**
- Full docker-compose stack brought up (`make up`) against a freshly-wiped volume set: Postgres 16, Neo4j 5 community, OpenSearch 2.18, MinIO all healthy; migrator completed Alembic `0002` → `constraints.cypher` → three OpenSearch index templates in one pass.
- `tests/integration/test_phase1_persistence.py` — 5/5 passed end-to-end (Pydantic validation, Postgres round-trip, Neo4j round-trip, Neo4j upsert idempotency, OpenSearch round-trip) against the live stack with host-side env overrides `POSTGRES_HOST=localhost NEO4J_URI=bolt://localhost:7687 OPENSEARCH_URL=http://localhost:9200 MINIO_ENDPOINT=localhost:9000 ENV=ci`.
- `tests/smoke/` — 105 passed, 2 skipped. The two skips are `test_healthz` / `test_readyz_all_green`, blocked on an unrelated `apps/api/Dockerfile` drift that needs its own fix (see "Open drift" below). All four backing-store connectivity tests, the Phase-1 migration-artifact checks, and the 89-check alignment audit are green against the live stack.
- After `make down -v` (volumes wiped) and a local Neo4j restart, `scripts/neo4j_load_phase1_local.py` loaded the same fixture set into the user's persistent local Neo4j (Homebrew, `bolt://localhost:7687`, database `neo4j`): wiped 775 pre-existing nodes / 32498 relationships / 5 constraints, re-applied the 12 Phase-1 unique constraints, upserted all 12 fixture nodes, merged all 11 Phase-1 relationships, verified counts (12 labels × 1, 11 rel types × 1). Dataset persists in the local Neo4j for browsing at http://localhost:7474.
- **Follow-up — `apps/api/Dockerfile` fix (2026-04-22)**: The initial run exposed that the API image was built with `uv pip install <flat list>` and never installed the `civic_common` / `civic_clients` workspace packages, so `docker-api-1` exited 1 on boot and the two API smoke tests (`test_healthz`, `test_readyz_all_green`) were skipped. Fix landed: `apps/api/Dockerfile` rewritten as a two-layer `uv sync --package civic-api --frozen --no-dev` against the workspace; `infra/docker/docker-compose.override.yml` bind-mount updated from `/app/src` to `/app/apps/api/src`. Second `make up` run: all five services healthy including `docker-api-1`, `docker compose exec api python -c "from civic_clients import postgres; from civic_common.settings import get_settings"` succeeds, `GET /healthz` returns `{"status":"ok"}`, `GET /readyz` returns `{"status":"ready","components":{"postgres":true,"neo4j":true,"opensearch":true,"minio":true}}`. `make down -v` + `neo4j start` restored the local Neo4j with its persistent fixture dataset intact.

---

## In progress

_No active phases — Phase 2 + 2.5 live validation completed 2026-04-26. Next: Phase 3 + 4 live validation._

---

### Phase 2 — First ingestion family (parallel bootstrap) — 2026-04-23
Plan: `/Users/idan/.cursor/plans/phase_2_ingestion_parallel_c42ebf68.plan.md`. Four waves: A (foundations ×5), B (Knesset adapters ×5), C (acceptance + static audit), D (docs sweep).

**Wave A — Foundations**
- **A1 — Archival service** (`services/archival/`). New workspace member `civic-archival`. `Fetcher` (httpx with polite defaults, `User-Agent: civic-proof-il/0.2`, `retry-after` honored once); `FetchResult` dataclass with UTC-aware `fetched_at`; `archive_payload()` is idempotent on `content_sha256` (returns `created=False` for known-hash payloads, otherwise writes to MinIO via `civic_clients.minio_client.put_archive_object` + inserts into `raw_fetch_objects`). `extension_from_content_type()` covers json/xml/pdf/html/csv/txt and falls back to `bin`. `python -m civic_archival fetch <url>` CLI for VCR-record workflow.
- **A2 — Source manifests** (`services/ingestion/_common/` + `data_contracts/jsonschemas/source_manifest.schema.json`). New workspace member `civic-ingest`. Pydantic `SourceManifest` model (extra=forbid, populate_by_name=True); JSON Schema kept in lock-step by alignment audit. Five Knesset manifests under `services/ingestion/knesset/manifests/*.yaml`: people, committees, votes, sponsorships, attendance. Each declares `family`, `adapter`, `source_url`, `source_tier` (1-3), `parser`, `cadence_cron`, and `entity_hints`.
- **A3 — Postgres-native job queue** (`infra/migrations/versions/0003_jobs_queue.py` + `civic_ingest.queue` + `civic_ingest.handlers` + worker upgrade). Single `jobs` table; `kind ∈ {fetch,parse,normalize,upsert}`, `status ∈ {queued,running,done,failed,dead_letter}`. `claim_one()` uses `FOR UPDATE SKIP LOCKED` inside a CTE, atomically transitioning the highest-priority runnable row to `running` and bumping `attempts`. `mark_failed()` re-queues with `run_after = now() + attempts²s` until `attempts ≥ max_attempts` then dead-letters. `civic_ingest.handlers.register(kind, adapter=…)` + `.dispatch(job)` provide a decorator registry so adapters own their own handlers. `IngestRun` context manager owns the `ingest_runs` row lifecycle (`running` on enter → `succeeded`/`failed` on exit). Worker's `apps/worker/src/worker/main.py` upgraded from Phase-0 stub: `run_once()` imports `civic_clients.postgres.make_connection`, falls back to the Phase-0 `{env,ok:True}` response if Postgres is unreachable (test safety), otherwise claims one job, dispatches, and commits. `apps/worker/pyproject.toml` now depends on `civic-common` + `civic-ingest` (workspace deps).
- **A4 — Entity resolution MVP** (`infra/migrations/versions/0004_entity_resolution_aliases.py` + `services/entity_resolution/`). New workspace member `civic-entity-resolution`. `entity_aliases` table with unique `(entity_kind, alias_text, alias_locale)` triple. `civic_entity_resolution.resolve()` implements plan steps 1-4 in order: (1) official external IDs via Neo4j label lookup, (2) exact normalized Hebrew match, (3) curated alias lookup (Hebrew then English), (4) transliteration normalization. Returns `ResolveResult` with `status ∈ {resolved, ambiguous, unresolved}`. Ambiguous `person` candidates write to the Phase-1 `entity_candidates` table (person-scoped by Phase-1 schema; other kinds skipped until Phase-3 extends the table). Steps 5 (fuzzy) + 6 (LLM) deferred. `normalize_hebrew()` strips niqqud / NFC-normalizes / collapses whitespace; `transliterate_hebrew()` is a deterministic 22-letter table.
- **A5 — Worker test hygiene**. New `apps/worker/tests/conftest.py` pins `ENV=dev` at conftest-load time (symmetric with `apps/api/tests/conftest.py`). `apps/worker/tests/test_smoke.py::_env` fixture now does `monkeypatch.delenv("ENV", raising=False)` before `monkeypatch.setenv("ENV", "dev")` so workspace-wide `pytest` runs (which load sibling conftests that set `ENV=test`) don't poison this test. Resolves the Phase-0 "Open drift" entry.

**Wave B — Five Knesset adapters**
Each adapter is its own workspace member under `services/ingestion/knesset/<name>/` with the same shape: `parse.py` (OData row → dict), `normalize.py` (dict → `Normalized…` dataclass with deterministic `uuid5(NS, "knesset_<kind>:<ext_id>")` IDs), `upsert.py` (Normalized… → Neo4j via `civic_clients.neo4j.run_upsert` against the Phase-1 templates), `cli.py` (`python -m civic_ingest_<name> run --dry-run`). All five share the `civic_ingest.adapter.run_adapter()` runner which walks `@odata.nextLink` pagination, drives `archive_payload()` per page, and accumulates stats onto the active `IngestRun`. Synthetic OData-shaped fixtures live under `tests/fixtures/phase2/cassettes/<adapter>/sample.json`; real VCR recording is a documented follow-up (see `docs/conventions/cassette-recording.md`).

- **B1 — people** (`civic-ingest-people`). `KNS_Person` → `Person` (Hebrew + English names, `external_ids={"knesset_person_id": …}`) + `Party` + `Office` (kind `mk`/`minister`/`deputy_minister`/`prime_minister`) + `MEMBER_OF` + `HELD_OFFICE`. 4 unit tests green.
- **B2 — committees** (`civic-ingest-committees`). `KNS_Committee` → `Committee` + one `MembershipTerm` + `MEMBER_OF_COMMITTEE` per listed member. 2 unit tests green.
- **B3 — votes** (`civic-ingest-votes`). `KNS_Vote` → `VoteEvent` (linked by `bill_id` when `BillID` is present) + one `CAST_VOTE` per detail row. Vote value is mapped from Hebrew (`בעד`/`נגד`/`נמנע`) and integer (`1`/`2`/`3`) forms; unknown values are silently dropped (matches the `CAST_VOTE` template's `IN ['for','against','abstain']` WHERE guard). 2 unit tests green.
- **B4 — sponsorships** (`civic-ingest-sponsorships`). `KNS_Bill` → `Bill` + `SPONSORED` edge per initiator (deduped on person UUID). 2 unit tests green.
- **B5 — attendance** (`civic-ingest-attendance`). `KNS_CmtSessionAttendance` → `AttendanceEvent`. Attendees are captured on the normalized bundle but not yet persisted as edges — the Phase-1 Neo4j templates don't include an `ATTENDED` relationship, so that's a Phase-3 extension. 2 unit tests green.

**Wave C — Acceptance + static audit**
- `tests/integration/test_phase2_ingestion.py` — live-stack end-to-end test. Runs all five adapters against the fixture cassettes using a stub fetcher (so no live HTTP), asserts `raw_fetch_objects` accumulated 5 rows, `ingest_runs.status = 'succeeded'`, Neo4j has the expected nodes + `MEMBER_OF` / `SPONSORED` / `CAST_VOTE` / `AttendanceEvent` counts, and re-running the people pipeline does not change the person count (idempotency). Marked `@pytest.mark.integration`, skips if the stack isn't up.
- `tests/smoke/test_alignment.py` gained ~20 Phase-2 parametrized checks: every adapter has a manifest, package (pyproject + parse/normalize/upsert/cli), and fixture file; both new migrations exist and mention their expected tables + check-constraint values; workspace `pyproject.toml` registers the 8 new members; `source_manifest.schema.json` has the five required fields. Alignment suite total: 112 tests, all green.
- `tests/smoke/test_migrations.py` gained `test_postgres_phase2_tables_exist` (requires `jobs` + `entity_aliases` when live Postgres is reachable).

**Wave D — Docs sweep** — this block, plus:
- ADRs `docs/adr/0002-vcr-record-replay.md`, `docs/adr/0003-postgres-native-job-queue.md`, `docs/adr/0004-source-manifest-format.md`.
- Conventions `docs/conventions/source-manifests.md`, `docs/conventions/cassette-recording.md`.
- `docs/ARCHITECTURE.md` Phase-2 section.
- Service READMEs for `services/archival/`, `services/ingestion/_common/`, `services/entity_resolution/`, `services/ingestion/knesset/`.

**Verification — unit tests only (2026-04-23)**
- `uv run pytest -q --ignore=tests/integration --ignore=tests/smoke/test_services.py --ignore=tests/smoke/test_migrations.py` → 216 passed, 2 skipped (the two skips are the live-stack-gated Phase-1 persistence tests).
- Per-adapter unit tests: 12/12 under `services/ingestion/knesset/`.
- Wave-A unit tests: 28/28 across `services/archival/`, `services/ingestion/_common/`, `services/entity_resolution/`, `apps/worker/`.
- Alignment audit: 112/112 (was 94 pre-Phase-2).
- **Live-stack run deferred.** `tests/smoke/test_services.py` + `test_migrations.py` + `tests/integration/test_phase2_ingestion.py` still require `make up` + `migrator` to complete first. Gate is the same as Phase-1 (skip whole module if any of the four backing stores pings false).

### Phase 2 — Real-data re-run (2026-04-23)
Plan: `/Users/idan/.cursor/plans/real-data-tests_78e2993a.plan.md` ("Real-data tests everywhere + re-run Phase 2"). Replaces the synthetic Phase-2 cassette set + the hand-written Phase-1 contract fixtures with byte-for-byte recordings from real upstream Knesset endpoints, and re-pins every assertion against those recordings.

**Policy + tooling**
- `.cursor/rules/real-data-tests.mdc` (`alwaysApply: true`) codifies the new repo-wide rule: every fixture under `tests/fixtures/**` that represents domain data MUST be the raw bytes of a real upstream recording, captured via `python -m civic_archival fetch --out <path>`. Hand-crafted domain entities (people, parties, bills, votes, committees) are forbidden anywhere in the test suite, including unit tests and conftests. Cross-referenced from `default-developer.mdc` ("Test data: see `real-data-tests.mdc`") and added to the hard-rules section of `plan-assist-agent.mdc`.
- `services/archival/src/civic_archival/cli.py` extended with `--out PATH` (writes raw bytes to disk so cassettes can be captured), `--max-bytes` and `--max-lines` (truncate large CSV / HTML responses to keep cassettes ≤200 KB while still being a head-of-real bytes). `services/archival/tests/test_cli.py` covers all three flags.
- `make record-cassettes` → `scripts/record-cassettes.sh` is the single sanctioned way to refresh the Phase-2 cassette set. It walks every adapter, calls the recorder, and rewrites the sibling `SOURCE.md` provenance file (URL, capture date, SHA-256, truncation flags). Requires `full_network` because `knesset.gov.il` and `production.oknesset.org` are not in the default sandbox allowlist.
- `tests/smoke/test_alignment.py` gained `test_no_synthetic_placeholders_in_fixtures` — a new check that scans every `*.json` / `*.csv` fixture for telltale placeholder strings (`example.com`, the `00000000-0000-4000-8000-` placeholder UUID prefix, `"PersonID": 30800`, `Benjamin Netanyahu`, `בני גנץ`, `Sample body content`, `Bill X — Sample Legislation`, etc.) and fails the build if any reappear. `test_phase2_adapter_fixture_exists` was also widened to accept `sample.json` OR `sample.csv` and to require a sibling `SOURCE.md`.

**Recorded cassettes (real upstream bytes)**
- `tests/fixtures/phase2/cassettes/people/sample.json` — `KNS_Person?$orderby=PersonID&$top=…` from `knesset.gov.il/Odata/ParliamentInfo.svc/` (see 2026-04-23 "Historical MK coverage" follow-up below; was `$filter=IsCurrent eq true&$top=50` until that change).
- `tests/fixtures/phase2/cassettes/committees/sample.json` — `KNS_Committee?$filter=KnessetNum eq 25&$top=…` from the same endpoint.
- `tests/fixtures/phase2/cassettes/sponsorships/sample.json` — `KNS_Bill?$filter=KnessetNum eq 25&$top=…`.
- `tests/fixtures/phase2/cassettes/attendance/sample.json` — `KNS_CommitteeSession?$filter=KnessetNum eq 25&$top=…`. (Per-MK attendance is not exposed by `ParliamentInfo.svc`; attendees are a Phase-3 join.)
- `tests/fixtures/phase2/cassettes/votes/sample.csv` — `vote_rslts_kmmbr_shadow.csv` from `production.oknesset.org/pipelines/data/votes/`. The Knesset's official per-MK vote OData endpoint (`VotesData.svc`) is bot-protected (returns a 247 JS challenge), so the open-government oknesset CSV mirror is the realistic source. Truncated via `--max-lines` for repo-friendliness.
- Each adapter directory has a `SOURCE.md` documenting URL, capture date, SHA-256, and truncation; alignment audit enforces presence.

**Adapter realignment (real upstream is more normalized than the old synthetic shape)**
- **people** — `KNS_Person` carries only `PersonID`, `FirstName`, `LastName`, `GenderDesc`, `IsCurrent`, `LastUpdatedDate`. English names, birth year, and party/office are NOT in this feed; party/office are joins against `KNS_PersonToPosition` / `KNS_Faction` (Phase-3). `parse.py` and `normalize.py` updated accordingly; `NormalizedPerson` no longer carries `english_name`; `upsert_person` passes `english_name=None` to the Cypher template.
- **committees** — `KNS_Committee` has no embedded member list. `NormalizedCommittee.memberships` is now an empty tuple; membership rows come from a Phase-3 join.
- **sponsorships** — `KNS_Bill` has no embedded initiators. `NormalizedBill.sponsorships` is now empty; initiator rows come from a Phase-3 join. `status_id` mapped to a string `status:<code>`.
- **votes** — CSV-backed adapter. New `civic_ingest.parse_csv_page` parser feeds the same `run_adapter` orchestration; `civic_ingest.adapter.run_adapter()` accepts a `page_parser` kwarg; `votes/manifest.yaml` declares `parser: csv` and `source_tier: 2`; `data_contracts/jsonschemas/source_manifest.schema.json` enum extended to allow `"csv"`. `normalize_vote` was refactored to emit one `VoteEvent` with a single `CastVote` per CSV row (the Neo4j upsert idempotently merges duplicate `VoteEvent` nodes by external ID and creates one `CAST_VOTE` edge per `(person, vote_event)` pair). `upsert_vote` also `MERGE`s a stub `Person` node before each `CAST_VOTE` so the edge has both endpoints when the People pipeline hasn't yet ingested that MK (different Knesset terms, partial coverage); the People pass back-fills canonical attributes via `coalesce()`.
- **attendance** — `KNS_CommitteeSession` is used as the attendance "event" (per-MK attendance per session is the Phase-3 join). `NormalizedAttendanceEvent.attendees` is now empty.
- **OData V3 vs V4 pagination.** `civic_ingest.odata.parse_odata_page` accepts both `odata.nextLink` (V3) and `@odata.nextLink` (V4) keys — the Knesset OData feed is V3 in practice despite the manifest URL hinting otherwise.
- **`UPSERT_ROOT` / `REPO_ROOT` off-by-one in every adapter.** All five adapters declared `Path(__file__).resolve().parents[5]` for both `infra/neo4j/upserts/` and the manifest path; `parents[5]` resolves to `services/`, not the repo root. Bug was masked while the synthetic Phase-2 integration test was the only thing exercising the upsert path with mocks; the real-data run surfaced it. Fixed: `parents[6]` in all five `upsert.py` and all five `cli.py` files. `infra/neo4j/upserts/person_upsert.cypher` declares `external_ids` as a JSON-encoded string (Neo4j Community can't store a Map property); `tests/integration/test_phase1_persistence.py::_person_params` now `json.dumps()` the dict before passing to the template.

**Phase-1 contract fixtures regenerated from real Phase-2 cassettes**
- `scripts/generate-phase1-fixtures.py` programmatically regenerates all 12 Phase-1 fixtures by reading the first row of the relevant Phase-2 cassette, passing it through the adapter's `parse → normalize` chain, and dumping the resulting Pydantic-shaped JSON. Domain UUIDs are the real `uuid5(PHASE2_UUID_NAMESPACE, "<kind>:<external_id>")` (PHASE2_UUID_NAMESPACE = `00000000-0000-4000-8000-00000000beef`). `source_document.json` and `evidence_span.json` are anchored to a real recorded `KNS_Person` OData response stored at `tests/fixtures/phase1/protocol/source_protocol.json`; `archive_uri` and `content_sha256` are computed from those bytes (so the fixtures match what production would archive). `atomic_claim.json` and `verdict.json` carry the real person UUID (`speaker_person_id` / `target_person_id`) and the real archived-source `archive_uri`; their narrative text is a clearly-labelled Phase-3 placeholder per the rule.
- `tests/fixtures/phase1/SOURCE.md` documents the derivation (which Phase-2 cassette feeds which Phase-1 fixture, the UUID5 logic, and the regeneration command).

**Test results — 2026-04-23 (live `make up` stack)**
- Unit tests + alignment audit: `uv run pytest -q --ignore=tests/integration --ignore=tests/smoke/test_services.py --ignore=tests/smoke/test_migrations.py` → **242 passed**.
- Per-adapter unit tests: 12/12 under `services/ingestion/knesset/` (re-pinned to the first real row of each cassette).
- Alignment audit: 162/162 — includes the new placeholder-scan and SOURCE.md presence checks.
- Phase-1 integration: `tests/integration/test_phase1_persistence.py` → **5/5 passed** against the live stack (Pydantic, Postgres, Neo4j, Neo4j-idempotency, OpenSearch round-trips, all using the regenerated real-data fixtures).
- Phase-2 integration: `tests/integration/test_phase2_ingestion.py` → **2/2 passed**. The roundtrip test now asserts presence of all five distinct `content_sha256` archive hashes in `raw_fetch_objects` (rather than count-by-`ingest_run_id`, which is fragile because the archive layer is content-addressed and dedup'd globally), Person + Committee + Bill + VoteEvent + AttendanceEvent nodes in Neo4j, and at least one `CAST_VOTE` edge from the votes CSV. The MEMBER_OF / SPONSORED edge assertions were removed — those are Phase-3 joins that are intentionally absent from the Phase-2 real-data shape.

### Phase 2 — Historical MK coverage (People cassette widening) — 2026-04-23
Plan: ad-hoc follow-up to the real-data re-run. Problem surfaced during live Neo4j inspection: the votes adapter's `CAST_VOTE` edges landed on a single anonymous stub Person (source_tier=2, all other properties NULL). Root cause: the People manifest carried `$filter=IsCurrent eq true`, so the recorded People cassette only included current (Knesset-25) MKs, while the oknesset votes CSV is Knesset-16 (MK בנימין אלון, `PersonID=405`). The two datasets never overlapped, so the People pipeline's `coalesce()` back-fill had nothing to match on.

**Resolution — Option A (widen the People manifest).**
- `services/ingestion/knesset/manifests/people.yaml`: `source_url` changed from `…KNS_Person?$format=json&$filter=IsCurrent eq true` to `…KNS_Person?$format=json&$orderby=PersonID`. The filter is dropped entirely — `KNS_Person` is a dimension table (one row per unique person ever in the Knesset), so a full scan is what we actually want. `$orderby=PersonID` makes the first-row pin stable across re-records.
- `scripts/record-cassettes.sh`: People recorder URL updated to `$orderby=PersonID&$top=500`. Knesset's OData server caps pages at 100 rows and emits `@odata.nextLink` for continuation; the production adapter walks the full set via `iter_odata_pages`, but the cassette captures only the first page (100 rows, ~22 KB on disk) — enough to cover `PersonID=405` (Benjamin Elon) and prove the back-fill.
- Re-recorded cassette: `tests/fixtures/phase2/cassettes/people/sample.json` — 100 rows, PersonID range 48..535, SHA-256 `510d644643e2240ddcf61559bfeda8c7efb204e81490fe2f1ed29153c58793ae`, IsCurrent distribution 6 True / 94 False. `SOURCE.md` regenerated.
- Phase-1 fixture anchor moved from PersonID=134 (אלינור ימין, current) to PersonID=48 (ירדנה מלר-הורוביץ, historical). `tests/fixtures/phase1/protocol/source_protocol.json` re-recorded against `KNS_Person?$filter=PersonID eq 48&$top=1`; `scripts/generate-phase1-fixtures.py` refactored to take the PersonID + IsCurrent from the first row of the people cassette rather than hard-coding `134` in strings. All 12 Phase-1 fixtures regenerated with deterministic `uuid5` keys (person_id `392c5ef2-b7c6-5c5a-b46a-2a3ead31e209`).
- Test updates: `services/ingestion/knesset/people/tests/test_people.py` re-pins first-row assertions (PersonID=48 / ירדנה מלר-הורוביץ / IsCurrent=False / 100 rows) and adds two new regression tests — `test_cassette_covers_historical_mks_referenced_by_votes_cassette` and `test_normalize_historical_mk_referenced_by_votes_cassette` — which assert the PersonID=405 row is present and normalizes to `hebrew_name="בנימין אלון"`.

**Live verification — 2026-04-23**
- `uv run pytest -q --ignore=tests/integration --ignore=tests/smoke/test_services.py --ignore=tests/smoke/test_migrations.py` → **244 passed** (was 242; +2 for the new historical-MK regression tests).
- Integration: `tests/integration/ -m integration` → **7/7 passed** against live `make up` stack (Phase-1 persistence 5/5 + Phase-2 ingestion 2/2).
- Neo4j post-run state:

  ```
  MATCH (p:Person)-[:CAST_VOTE]->(:VoteEvent)
  RETURN p.canonical_name, p.hebrew_name, p.source_tier, count(*)
  ```

  Single row: `בנימין אלון / בנימין אלון / tier=1 / 100 edges`. Total Person nodes: 144, nameless stubs: **0** (was 1 before the fix). The `coalesce()`-based back-fill in `person_upsert.cypher` works as designed once both pipelines reference the same deterministic `uuid5(NS, "knesset_person:405")` key.

---

### Phase 2.5 — Join adapters (2026-04-23)
Plan: `/Users/idan/.cursor/plans/phase_2.5_join_adapters_3218fd28.plan.md`. Closes the five relationship lanes the Phase-2 real-data re-run intentionally left empty because `KNS_Person` / `KNS_Bill` / `KNS_Committee` / `KNS_CommitteeSession` don't embed the joins. Three new adapters + one existing adapter extension populate `MEMBER_OF`, `HELD_OFFICE`, `MEMBER_OF_COMMITTEE`, `SPONSORED`, and `ATTENDED`.

**New adapter — `positions`** (`civic-ingest-positions`, `services/ingestion/knesset/positions/`)
- Source: `KNS_PersonToPosition` (Tier-1 OData). Recorded cassette: `tests/fixtures/phase2/cassettes/positions/sample.json` — Knesset-25 slice (`$filter=KnessetNum eq 25&$top=200`), 200 rows.
- Emits zero-to-two relationship lanes per row: `(:Person)-[:MEMBER_OF]->(:Party)` when `FactionID` is populated, `(:Person)-[:HELD_OFFICE]->(:Office)` when `PositionID` is populated (always — `PositionID` is NOT NULL on every upstream row).
- Does NOT emit committee memberships — see "`CommitteeID` is 100% NULL in `KNS_PersonToPosition`" gotcha below. `committee_memberships` is a separate adapter.
- `NormalizedPositionBundle` carries three optional lanes (`party`, `office`, `committee`) so the same dataclass could in principle back a future Tier-1 committee source; v1 populates only `party` and `office`.
- Office UUID is composite: `uuid5(PHASE2_UUID_NAMESPACE, f"knesset_office:{PositionID}:{GovMinistryID or '-'}")`. "Minister of Defense" and "Minister of Education" are two distinct Office nodes even though both share `PositionID=55` (minister).
- Upsert issues up to 5 `run_upsert` calls per bundle: stub `Person` MERGE → `Party` MERGE + `MEMBER_OF` → `Office` MERGE + `HELD_OFFICE`. All endpoint MERGEs precede the relationship MERGE because the Phase-1 relationship templates `MATCH` both endpoints.

**New adapter — `bill_initiators`** (`civic-ingest-bill-initiators`, `services/ingestion/knesset/bill_initiators/`)
- Source: `KNS_BillInitiator` (Tier-1 OData). Recorded cassette: `tests/fixtures/phase2/cassettes/bill_initiators/sample.json` — `$orderby=BillInitiatorID desc&$top=100` (100 most recent rows).
- Emits `(:Person)-[:SPONSORED]->(:Bill)` edges. Co-signatory rows (`IsInitiator=False`) are filtered out in `parse.py` for v1 — only primary bill initiators become SPONSORED edges.
- Upsert: stub `Person` + stub `Bill` MERGE (both with NULL non-key properties so the people and sponsorships adapters back-fill via `coalesce()`), then the `SPONSORED` edge.

**New adapter — `committee_memberships`** (`civic-ingest-committee-memberships`, `services/ingestion/knesset/committee_memberships/`)
- Source: `mk_individual_committees.csv` (Tier-2 CSV from `production.oknesset.org/pipelines/data/members/mk_individual/`). Recorded cassette: `tests/fixtures/phase2/cassettes/committee_memberships/sample.csv` — 100-row head of the live dataset.
- Emits `(:Person)-[:MEMBER_OF_COMMITTEE]->(:Committee)` edges with `valid_from` / `valid_to` temporal bounds parsed from CSV `from_date` / `to_date`.
- Why Tier-2 and not Tier-1 OData: Knesset's `KNS_PersonToPosition` declares `CommitteeID` / `CommitteeName` columns but 0 of 11,090 rows have them populated (April 2026). Committee memberships are only published as structured data through the oknesset open-government mirror.
- Resolves CSV `mk_individual_id` → canonical Knesset `PersonID` via the shared `MkIndividualLookup` (see below). Unresolved `mk_individual_id`s are dropped with a structured-log warning rather than creating orphan nodes.

**Extended adapter — `attendance`**
- Manifest flipped from Tier-1 OData `KNS_CommitteeSession` to Tier-2 CSV `kns_committeesession.csv` from `production.oknesset.org/pipelines/data/people/committees/meeting-attendees/`. The OData endpoint doesn't expose attendees; the oknesset CSV mirror republishes the same sessions enriched with `attended_mk_individual_ids` (a Python-literal list column).
- Cassette format changed from `sample.json` to `sample.csv`. Re-recorded with `--max-lines 51` so the first ~50 rows cover both empty and populated attendee arrays.
- `parse.py` rewritten for CSV columns; `normalize.py` gained a `NormalizedAttendee` dataclass and now populates `NormalizedAttendanceEvent.attendees` (previously hardcoded to `()`), using `MkIndividualLookup` to resolve each `mk_individual_id`. Presence is hardcoded to `"present"` for v1 — absentee rows don't exist in this source.
- `upsert.py` now MERGEs a stub `Person` before each `ATTENDED` edge (same pattern as votes adapter — attendees may not yet exist in the people pipeline's coverage).

**New shared utility — `civic_ingest.mk_individual_lookup`**
- `MkIndividualLookup` + `load_mk_individual_lookup()` in `services/ingestion/_common/src/civic_ingest/mk_individual_lookup.py`.
- Parses `mk_individual.csv` (the shared dimension table, NOT an adapter source) and exposes `resolve(mk_individual_id) -> PersonID` / `get(mk_individual_id, default=None)`.
- Default fixture lives at `tests/fixtures/phase2/lookups/mk_individual/sample.csv` (under `lookups/` not `cassettes/` because it's consumed by adapters, not ingested into the graph). Full 1184-row recording of the live dataset.
- `@lru_cache(maxsize=1)` on the default-path loader so per-process the CSV is parsed once. Production CLIs call `load_mk_individual_lookup(bytes_payload)` with fresh bytes fetched at runtime.

**Cross-cutting changes**
- `data_contracts/jsonschemas/source_manifest.schema.json` `adapter` enum extended: `positions`, `bill_initiators`, `committee_memberships` added (total 8 adapters).
- `civic_ingest.manifest.AdapterKind` `Literal` extended with the same three values — JSON Schema and Pydantic stay in sync.
- `pyproject.toml` `[tool.uv.workspace].members` extended with the three new service paths.
- `apps/api/Dockerfile` extended with three `COPY` lines for the new service packages (per the Phase-3/4 gotcha: every workspace member's source must be present in the build context, not just the api's direct deps).
- `tests/smoke/test_alignment.py::PHASE2_ADAPTERS` extended with the three new adapter names; the existing parametrized alignment checks (`test_phase2_manifest_exists`, `test_phase2_adapter_package_exists`, `test_phase2_adapter_fixture_exists`) automatically cover them.
- `scripts/record-cassettes.sh` extended with recorders for `positions`, `bill_initiators`, `committee_memberships`, the new attendance CSV source, and the shared `mk_individual` lookup.
- `tests/integration/test_phase2_ingestion.py` extended from 5 to 8 adapters (`positions`, `bill_initiators`, `committee_memberships` added to the adapter loop; attendance switched to the CSV page parser + lookup-injected normalize). New edge-count assertions: `MEMBER_OF`, `HELD_OFFICE`, `MEMBER_OF_COMMITTEE`, `SPONSORED`, `ATTENDED` each required to have count ≥ 1.

**Verification — unit tests (2026-04-23)**
- Per-adapter unit tests: 26/26 across `positions`, `bill_initiators`, `committee_memberships`, and the extended `attendance`. Alignment audit: 184/184. Integration test collects and imports cleanly; live-stack run deferred to the next `make up` session (skips gracefully otherwise).

---

### Phase 3 — Atomic claim pipeline (parallel agents, 2026-04-23)
Plan: `/Users/idan/.cursor/plans/phase3-phase4-parallel-agents_4397439f.plan.md`. Wave 1 delivered nine foundation write-lanes (A1–A9) covering slot templates, rule-first decomposer, LLM fallback + prompt cards, temporal normalizer, checkability classifier, entity-resolution v2, the ATTENDED graph edge, the real-data statement gold set, and statement-intake persistence.

**Ontology (A1)**
- `packages/ontology/src/civic_ontology/claim_slots.py` declares a `SlotTemplate` per `ClaimType` (six templates: `vote_cast`, `bill_sponsorship`, `office_held`, `committee_membership`, `committee_attendance`, `statement_about_formal_action`). `validate_slots(claim_type, slots)` returns a list of violation strings (empty when valid).
- `civic_ontology.schemas.check_schemas` now also validates that `SLOT_TEMPLATES` covers every `ClaimType` value and no extraneous templates exist — drift blows up the CI gate.

**Claim decomposition (A2 + A3)**
- `services/claim_decomposition/src/civic_claim_decomp/` ships rules-first decomposition with Hebrew + English regex templates per claim family, an `LLMProvider` fallback protocol, and a deterministic `StubProvider` for hermetic tests. Every candidate runs through `validate_slots` before emission; overlapping rule matches are resolved longest-span-first.
- `packages/prompts/src/civic_prompts/` exposes `load_card(category, version)` reading YAML from `decomposition/`, `temporal_normalization/`, `summarize_evidence/`, `reviewer_explanation/`. All four categories ship a `v1.yaml` with system + user templates + metadata.

**Temporal normalization (A4) + Checkability (A5)**
- `services/normalization/src/civic_temporal/` parses ISO dates, year-only phrases, Hebrew months, Knesset terms (`KNESSET_TERMS` constant), `"last year"` / `"last term"` relative phrases into `TimeScope(start, end, granularity)`. Unknown phrases return `granularity="unknown"`, never raise.
- `civic_claim_decomp.checkability.classify(CheckabilityInputs(...))` returns one of `checkable`, `insufficient_entity_resolution`, `insufficient_time_scope`, `non_checkable`.

**Entity resolution v2 (A6)**
- Migration `0005_polymorphic_entity_candidates.py` renames `resolved_person_id` → `canonical_entity_id` and adds `entity_kind` so non-person entities can be queued.
- Resolver ladder now has six steps: alias → exact Hebrew → exact English → external-id crosswalk → rapidfuzz fuzzy (`FUZZY_RESOLVE_THRESHOLD=92`, `FUZZY_MARGIN=5`) → optional `LLMEntityTiebreaker` protocol.

**Graph edges (A7)**
- `infra/neo4j/upserts/relationships/attended.cypher` declares `(:Person)-[:ATTENDED {presence}]->(:AttendanceEvent)`. Attendance ingest adapter upserts one `ATTENDED` edge per attendee per session. Relationship count grows from 11 → 12.

**Gold set + intake persistence (A8 + A9)**
- `scripts/record-statements.py` downloads a statement URL, extracts the excerpt, and writes `tests/fixtures/phase3/statements/<slug>/{statement.txt, SOURCE.md, labels.yaml}`. Enforced by `test_alignment.py::test_gold_set_statements_have_pinned_labels` + the existing real-data-tests policy.
- Migration `0006_statements.py` creates `statements` + `statement_claims` tables. `civic_claim_decomp.persistence.persist_statement` inserts both in one transaction.

**Live verification (Wave 3)**
- `tests/integration/test_phase3_claim_pipeline.py` exercises the decomposer + temporal normalizer + checkability classifier as a pipeline, hermetically.
- 194 tests green under `uv run pytest tests/` (Phase-0/1/2 checks remain green; 4 pre-existing neo4j connectivity tests still require `make up`).

### Phase 4 — Retrieval + verdict engine (parallel agents, 2026-04-23)

**Graph retrieval (B1)**
- `services/retrieval/src/civic_retrieval/graph.py` loads one Cypher template per claim_type from `infra/neo4j/retrieval/` (six templates: `vote_cast.cypher`, `bill_sponsorship.cypher`, `office_held.cypher`, `committee_membership.cypher`, `committee_attendance.cypher`, `statement_about_formal_action.cypher`) and returns typed `GraphEvidence` records.

**Lexical retrieval (B2)**
- `services/retrieval/src/civic_retrieval/lexical.py` issues BM25 + optional kNN queries against OpenSearch `evidence_spans`. Template `0002_evidence_spans.json` now declares `normalized_text` (BM25 analyser) + `embedding` (`knn_vector`, 384-dim).

**Deterministic reranker (B3)**
- `services/retrieval/src/civic_retrieval/rerank.py` combines five weighted signals (source tier, directness, temporal alignment, entity resolution, cross-source consistency) into a single overall score. `WEIGHTS` is the one true axis-importance constant — also consumed by the verification rubric.

**Verdict engine + rubric (B4)**
- `services/verification/src/civic_verification/engine.py` implements `decide_verdict(VerdictInputs)` mapping `(claim_type, ranked_evidence, checkability)` → `VerdictOutcome(status, confidence, needs_human_review, reasons)`. Thresholds: `ABSTAIN_OVERALL=0.45`, `HUMAN_REVIEW_OVERALL=0.62`.
- `civic_verification.compute_confidence(ranked)` returns the five-axis `Confidence` vector using reranker weights.

**Provenance bundler (B5)**
- `civic_verification.bundle_provenance(outcome, ranked, ...)` returns `ProvenanceBundle(verdict, top_evidence, uncertainty_note)`. Optional `EvidenceSummarizer` protocol is the only LLM seam and can never alter verdict fields.

**API wiring (C1)**
- `apps/api/src/api/routers/` now ships three routers: `claims.py` (`POST /claims/verify`), `persons.py` (`GET /persons/{id}`), `review.py` (`GET /review/tasks`, `POST /review/tasks/{id}/resolve`). `pipeline.py` composes decomposition → resolution → retrieval → verdict behind a `VerifyPipeline` dependency-injectable seam.

**Integration tests + alignment (C2)**
- New: `tests/integration/test_phase3_claim_pipeline.py`, `tests/integration/test_phase4_retrieval_verdict.py`, `tests/integration/test_verify_end_to_end.py`.
- Extended `tests/smoke/test_alignment.py` with ~40 new rows covering: 6 slot-template registrations × 6 graph-retrieval templates = 12 parametrized rows + 28 singleton assertions over rerank signals, OpenSearch mapping, verification module exports, abstention-threshold names, API router modules, API `main.py` router wiring, API pyproject deps, prompt loader surface, migrations 0005/0006, entity-resolution v2 symbols, claim-decomposition surface, temporal-normalizer exports, and gold-set label pinning.

**Review workflow MVP (C3)**
- `services/review/src/civic_review/` implements `PostgresReviewRepository` with atomic `UPDATE review_tasks` + `INSERT INTO review_actions` in one transaction. Five allowed actions (`approve`, `reject`, `relink`, `annotate`, `escalate`) match migration 0002's CHECK. `annotate` is non-terminal (keeps the task `open`); the others close the task. Terminal tasks still record audit trail for attempted follow-ups.
- `POST /review/tasks/{id}/resolve` returns the updated task dict; 404 when missing; 422 on invalid decision vocabulary.

**Docs sweep (Wave 4)**
- This entry + ADRs 0005-0008, three new `docs/conventions/*.md` pages, refreshed `docs/ARCHITECTURE.md` Phase-3/4 sections, service READMEs under every new `services/*/` package.

### Phase 2 + 2.5 live validation — 2026-04-26

- Full `make up` → compose stack brought up (Postgres 16, Neo4j 5, OpenSearch 2.18, MinIO, migrator, API, worker — all healthy).
- Migrator container applied Alembic migrations (including `0003_jobs_queue` + `0004_entity_resolution_aliases`) + Neo4j constraints + OpenSearch templates on first boot.
- `tests/integration/test_phase2_ingestion.py` — **2/2 passed** against the live compose stack. All 8 adapters (people, committees, votes, sponsorships, attendance, positions, bill_initiators, committee_memberships) exercised end-to-end with real-data cassettes via stub fetcher.
- `tests/integration/test_phase1_persistence.py` — **5/5 passed** (Pydantic, Postgres, Neo4j, Neo4j-idempotency, OpenSearch round-trips).
- Neo4j post-run state — 6 relationship types confirmed:
  - `ATTENDED`: 272 edges
  - `CAST_VOTE`: 100 edges
  - `HELD_OFFICE`: 100 edges
  - `MEMBER_OF`: 98 edges
  - `MEMBER_OF_COMMITTEE`: 90 edges
  - `SPONSORED`: 76 edges
- Node counts: Person 267, VoteEvent 100, AttendanceEvent 70, Bill 42, Committee 34, Party 8, Office 2.
- Host-side env-var override required (documented gotcha): `Settings` has `env_file=None`, so all env vars must be exported explicitly when running tests from the host. Four hostnames must be swapped to `localhost` (`POSTGRES_HOST`, `NEO4J_URI`, `OPENSEARCH_URL`, `MINIO_ENDPOINT`) plus all credential vars.

---

## Remaining pipeline — priority order

| # | Phase | Description | Priority |
|---|-------|-------------|----------|
| 1 | Phase 3 + 4 live validation | record ~25 gold-set statements via `scripts/record-statements.py`, pin labels, run `tests/integration/test_verify_end_to_end.py` against the live stack | high |
| 2 | Phase 5 — Reviewer UI + conflict queue | Full reviewer UI, conflict queue, verdict override with audit log UX (MVP Python surface shipped in Phase 4 C3) | medium |
| 3 | Phase 6 — Hardening + evaluation | Benchmark set, offline eval harness, regression tests, provenance completeness tests, freshness monitoring | medium |

Acceptance criteria and detailed deliverables for each phase are in [political_verifier_v_1_plan.md](political_verifier_v_1_plan.md).

> Phase 0, Phase 1, Phase 2, Phase 2.5, Phase 3, and Phase 4 moved to Completed milestones on 2026-04-21 / 2026-04-23. Phase 2 + 2.5 live validation completed 2026-04-26.

---

## Drift patches applied in Wave-2 audit (Agent G)

- Deleted `packages/ontology/tests/__init__.py` (Agent D's oversight): the Agent-E gotbook explicitly forbids `__init__.py` under `packages/*/tests/` because pytest's rootdir collection collides across packages with duplicate `tests.conftest` module names. Without this patch, `uv run pytest` at workspace root raised `ImportPathMismatchError`.
- Deleted `apps/worker/tests/__init__.py` (pre-existing Phase-0 drift, exposed once the ontology-tests collision was fixed). Same rationale: both `apps/api/tests` and `apps/worker/tests` would otherwise claim the `tests` package name and pytest picks one arbitrarily, breaking the other. After the deletion, `apps/worker/tests/test_smoke.py` imports cleanly when invoked workspace-wide.
- Registered `integration` marker in the workspace `pyproject.toml` `[tool.pytest.ini_options]` so `@pytest.mark.integration` no longer emits `PytestUnknownMarkWarning` and future runners can filter with `-m integration`.

No contract/schema/constraint drift required fixing — Wave 1 landed cleanly.

---

## Open drift (surfaced by the 2026-04-22 live validation)

- **RESOLVED 2026-04-22** — **`apps/api/Dockerfile` doesn't install the shared `civic_common` / `civic_clients` packages.** Agent E's refactor moved clients + settings into workspace packages, but the api image originally copied only `apps/api/pyproject.toml` and `apps/api/src`; `api.clients.minio_client`'s `from civic_clients.minio_client import ...` crashed at import with `ModuleNotFoundError`. Fix: `apps/api/Dockerfile` now does a two-layer `uv sync --package civic-api --frozen --no-dev` against the workspace (lockfile + every workspace pyproject first for dep-caching, then source + full install). `infra/docker/docker-compose.override.yml` updated to mount `apps/api/src` at `/app/apps/api/src` to match the new workspace layout. Verified: image builds, `from civic_clients import postgres, neo4j, opensearch, minio_client; from civic_common.settings import get_settings; from api.main import app` all succeed; `uvicorn api.main:app` starts and `/healthz` returns `{"status":"ok"}`. See the "Known gotchas (Phase 1)" bullet for the non-regression contract.
- **The migrator container succeeded cleanly in 2026-04-22**, so the original drift did not affect migrations, only the `api` service (and by extension, the API health/readiness smoke tests). Worker image was not affected — `apps/worker/src/worker/main.py` only imports `structlog` + its local `.settings` (which uses `pydantic_settings` directly, not `civic_common`).

---

## Cross-step knowledge

> Future agents: append persistent context here — gotchas, data quirks, design decisions, performance baselines, known limitations — so it survives across sessions.

### Design decisions

**Phase -1 / Phase 0**
- **Conservative abstention by default.** A verdict requires at least one Tier 1 source. Tier 1 conflicts must go to human review. No verdict without archived provenance.
- **LLM role is strictly limited.** LLMs may assist claim decomposition, temporal normalization, evidence summarization, and reviewer explanations. They must NOT make canonical fact promotion, conflict resolution between official records, or direct database writes.
- **Deterministic/rule-first everywhere.** Rules before LLM in decomposition and entity resolution. Deterministic verdict engine in v1; LLMs summarize evidence only.
- **Source tiers are enforced structurally.** Tier 1: official Knesset records, gov.il role pages, government decision records, official election results. Tier 2: contextual official material. Tier 3: discovery-only (media, watchdogs, mirrors).
- **uv + Python 3.12** adopted as the single Python toolchain across the workspace (`pyproject.toml` with `[tool.uv.workspace]`, members = apps/api, apps/worker, apps/migrator, packages/*).
- **Neo4j community edition with APOC** for the graph schema; Neo4j 5 takes the `NEO4J_AUTH=<user>/<password>` env-var contract (not `NEO4J_USERNAME`/`NEO4J_PASSWORD` — compose builds that string from our named vars).
- **OpenSearch 2 single-node** with security plugin disabled for dev (`DISABLE_SECURITY_PLUGIN=true`). `OPENSEARCH_INITIAL_ADMIN_PASSWORD` is still supplied because 2.12+ insists on it even when disabling security.
- **MinIO single-node server** used as the S3-compatible archive store; bucket `civic-archive` (name in `MINIO_BUCKET_ARCHIVE`).
- **One-shot `migrator` compose service** runs `alembic upgrade head` → `cypher-shell < constraints.cypher` → `PUT`s every OpenSearch index template; `api` and `worker` gate on `service_completed_successfully`.
- **Health semantics**: `/healthz` is liveness (always 200 if the process is alive); `/readyz` is readiness (503 if any backing store is down) and always returns the four component booleans.

**Phase 1 — Canonical data model**
- **UUID4 business keys everywhere.** Postgres keeps a surrogate `BIGSERIAL/Identity` integer PK plus a `<entity>_id UUID UNIQUE NOT NULL` business key; Neo4j MERGEs on the UUID string; OpenSearch `_id` is the same UUID; JSON Schemas declare `"format": "uuid"`.
- **Postgres owns pipelines, not facts.** `ingest_runs`, `raw_fetch_objects`, `parse_jobs`, `normalized_records`, `entity_candidates`, `review_tasks`, `review_actions`, `verification_runs`, `verdict_exports` — nothing else. Domain entities live in Neo4j.
- **Neo4j is the system of record for facts.** All 12 domain nodes + 11 relationships, with temporal validity (`valid_from`/`valid_to`) on `HELD_OFFICE`, `MEMBER_OF`, `MEMBER_OF_COMMITTEE`, and `MembershipTerm`.
- **OpenSearch is a cache and search index**, never a system of record. Three indexes: `source_documents`, `evidence_spans`, `claim_cache`. Dev defaults to strict dynamic mapping; `dynamic:"strict"` catches schema drift at ingest time.
- **MinIO is the immutable content-addressed archive.** `s3://<bucket>/<source_family>/<YYYY>/<MM>/<DD>/<sha256>.<ext>` — one URI per raw bytes; cross-bucket writes are a bug.
- **Contracts are Draft 2020-12 + Pydantic v2.** Hand-written schemas are canonical; Pydantic models are the typed Python surface. Drift-check CLI validates field-set equivalence, not byte equivalence of the generated schema.
- **`civic_common.settings` is the promoted `Settings` class.** Every service imports `get_settings()` from the shared package; no per-service duplication of env-var contracts.

### Phase-1 / contracts decisions (Agent D)
- **Hand-written JSON Schemas are canonical**, not `pydantic.model_json_schema()` output. Pydantic's generator emits cosmetically different Draft 2020-12 (auto `title`, `$defs` names, `anyOf: [{type: "string"}, {type: "null"}]` instead of `type: ["string","null"]`, etc.) — chasing byte-equivalence was more fragile than the field-set diff approach. Drift check compares `properties` keys and `required` lists between schema and Pydantic model; fixture-validation tests catch data-level regressions.
- **Nullable foreign keys in `AtomicClaim` are required keys, not optional fields.** The plan contract (lines 249-270) lists `speaker_person_id`, `target_person_id`, `bill_id`, `committee_id`, `office_id`, `vote_value` as `"uuid|null"` / `"for|against|abstain|null"` — meaning the **key must be present** but the value may be null. Pydantic models therefore declare them as `UUID | None` with no default, so `extra="forbid"` + explicit-null payload round-trips cleanly. Do not add `= None` defaults to these fields.
- **Schema `$ref` uses relative paths**, e.g. `"$ref": "common/time_scope.schema.json"`. Fixture validators register each schema under both its `$id` URL and its relative path inside `data_contracts/jsonschemas/` via `referencing.Registry` so both resolution modes work.
- **`populate_by_name=True` on every model** so schemas can be loaded from either Python-native or alias form in the future (no aliases yet, but the toggle is set).
- **`vote_value` enum includes a literal `null`** in the JSON Schema enum (`["for","against","abstain",null]`) — this is per the user's explicit instruction and faithful to the plan.

### Phase-1 / clients + settings decisions (Agent E)
- **`Settings` lives in `packages/common/src/civic_common/settings.py`.** `apps/api/src/api/settings.py` is a two-line re-export. Workers and clients import from `civic_common.settings` so the env-var contract has a single source of truth. `get_settings` is `@lru_cache`d; call `get_settings.cache_clear()` between env-var mutations in tests.
- **`apps/api/src/api/clients/*` is a thin re-export layer over `civic_clients`.** The legacy public names (`ping_postgres`, `ping_neo4j`, `ping_opensearch`, `ping_minio`, `get_pg_connection`, `get_neo4j_driver`, `get_opensearch_client`, `get_minio_client`) are preserved as module-level aliases on the `api.clients.<mod>` namespace. `health.py` routes through those aliases so the test suite can monkeypatch at `api.clients.postgres.ping_postgres` without reaching into the shared library. Do not shortcut health.py to call `civic_clients.postgres.ping` directly — it will break the monkeypatch surface.
- **`civic_clients.archive.SOURCE_FAMILIES = {"knesset", "gov_il", "elections"}`** is the whitelist for the archive URI's family segment. Mirrors Phase-0 `services/ingestion/*` subdirs. Adding a family is a two-step change (code + `docs/conventions/archive-paths.md`).
- **`build_archive_uri` reads the bucket from live `get_settings()` at call time**, not at import time. Changing `MINIO_BUCKET_ARCHIVE` and clearing the settings cache flips every freshly built URI. Archive URIs are intentionally NOT interned anywhere.
- **`captured_at` MUST be timezone-aware** everywhere that feeds `build_archive_uri`; naive datetimes raise `ValueError`. This prevents the single biggest class of archive-path drift (off-by-one-day paths from local-time timestamps).
- **`put_archive_object` asserts the URI's bucket equals `MINIO_BUCKET_ARCHIVE`.** Cross-bucket writes are a bug, never a feature.

### Phase-1 / live validation decisions (2026-04-22)
- **Two-instance Neo4j story.** (a) Compose `neo4j:5-community` is the automated-test Neo4j — wiped on every `make down -v` and re-initialized on every `make up` with whatever `NEO4J_PASSWORD` is in the repo `.env` at boot time. (b) The local Homebrew / Neo4j Desktop instance on `bolt://localhost:7687` (creds in `.cursor/.env` under `G_DB_*`) is the durable browsable dataset, managed via `scripts/neo4j_load_phase1_local.py`. Production will eventually introduce a third, managed instance. The two dev instances share host port 7687 and MUST NOT run simultaneously.
- **`scripts/neo4j_load_phase1_local.py` is standalone on purpose.** It parses `.cursor/.env` with a 20-line `load_dotenv` helper and talks to Neo4j through the raw `neo4j.GraphDatabase` driver — no `civic_common.Settings`, no `civic_clients.*`. This keeps the loader runnable on a machine where the full Phase-1 stack isn't configured (e.g. fresh clone, or when Postgres/OpenSearch/MinIO env vars aren't set). Do not refactor it to pull from `Settings` — that would couple the local-Neo4j workflow to the compose env contract.
- **The loader is persistent by design.** Unlike `tests/integration/test_phase1_persistence.py::_cleanup` which `DETACH DELETE`s everything on teardown, the loader leaves the dataset in place so you can explore it in Neo4j Browser. Re-running the loader is safe (it wipes first) but destructive — any ad-hoc experiments under the same DB will be erased.

### Known gotchas

**Phase 0**
- **Migrator Dockerfile pulls `cypher-shell_5.23.0_all.deb` from `dist.neo4j.org` at build time.** If Neo4j version is bumped or the URL changes, update `apps/migrator/Dockerfile`. cypher-shell is the Neo4j 5 client; major-version skew between client and server is usually fine but keep them in sync when possible.
- **Alembic URL is constructed in `env.py`**, not `alembic.ini`. `sqlalchemy.url` in `alembic.ini` is intentionally blank so the env-var contract is the single source of truth. Do not hardcode credentials there.
- **`scripts/run-migrations.sh` is dual-mode.** Inside the migrator container it uses `ROOT_DIR=/app`; on the host it resolves `ROOT_DIR` from its own location (`$(dirname "$0")/..`). Keep this behavior when extending.
- **`schema_migrations_info` table is a phase-0 bookkeeping placeholder.** Real domain schema starts in Phase 1; do not build on this table.
- **macOS Docker Desktop must be running** for `make up` — the stack cannot start if the Docker daemon is not up. Wave-2 Phase-1 audit deferred the full `make up` smoke run for this reason on the author's machine.
- **`uv` must be on PATH** for `make test` / `make smoke`. Use `scripts/bootstrap-dev.sh` (or `curl -LsSf https://astral.sh/uv/install.sh | sh`) first.
- **Scripts were committed with the `+x` bit set** (verified via `git ls-files --stage scripts/`). Fresh clones get executable scripts automatically; the `Makefile` also falls back to `bash scripts/<name>.sh` so either path works.
- **API tests import `api.main` at module load**, and `api.main` calls `create_app()` → `get_settings()` at module level. Per-test `monkeypatch` fixtures run too late — `apps/api/tests/conftest.py` also sets the required env vars with `os.environ.setdefault(...)` at conftest-load time. Do NOT remove that block without moving `app = create_app()` out of module scope first.
- **OpenSearch 2.12+ enforces strong admin passwords (min 8 chars, upper/lower/digit/special)** when the security plugin is enabled. Our compose sets `DISABLE_SECURITY_PLUGIN=true`, so `admin/admin` works. If anyone re-enables the security plugin, the password in `.env.example` must be upgraded (e.g. `Civic_Dev_Pw!2026`).
- **`tests/smoke/conftest.py` honors `*_HOST` env-var variants** (e.g. `POSTGRES_HOST_HOST`, `NEO4J_URI_HOST`, `OPENSEARCH_URL_HOST`, `MINIO_ENDPOINT_HOST`). This lets tests on the host machine hit the docker-compose published ports (`localhost:5432`, etc.) while the container-local `.env` still uses in-network hostnames (`postgres:5432`). Keep both when adding new backing stores.

**Phase 1**
- **Neo4j Community can't enforce relationship-property existence.** `REQUIRE r.<prop> IS NOT NULL` on a relationship is an Enterprise-only feature. We enforce the invariant inside the upsert templates in `infra/neo4j/upserts/relationships/` via `WHERE <prop> IS NOT NULL` guards; do NOT bypass those templates when writing rels from new code paths.
- **`sa.Identity(always=False)` is used instead of `BIGSERIAL` in `0002_phase1_domain_schema.py`.** Functionally equivalent (Postgres 10+ renders `BIGSERIAL` as `BIGINT GENERATED BY DEFAULT AS IDENTITY`); leave as-is.
- **Pydantic `AtomicClaim` nullable-FK fields are required keys with no default.** Declaring `speaker_person_id: UUID | None` without `= None` means the key must be present (possibly as `null`) for `extra="forbid"` models. Fixtures and all write paths must pass the key explicitly.
- **Tests in `packages/*/tests/` and `apps/*/tests/` must NOT have `__init__.py`.** pytest's rootdir mode otherwise conflates them into a single `tests` package and raises `ImportPathMismatchError: tests.conftest`. Wave-2 audit deleted two leftover `__init__.py` files (`packages/ontology/tests/__init__.py`, `apps/worker/tests/__init__.py`).
- **OpenSearch `text_he` analyzer is currently aliased to `standard`.** The mapping structure is ready for a real Hebrew analyzer (stemmer plugin or custom) — swap in Phase 2/6. Dev templates set `number_of_replicas: 0`; prod must override.
- **Archive URI extensions are lowercased and stripped of a leading `.` in `build_archive_uri`.** Parsing enforces `[a-z0-9]+` post-normalization; do not feed `.HTML` expecting a round-trip — it becomes `html`.
- **`captured_at` MUST be timezone-aware** anywhere it feeds `build_archive_uri` or the Postgres `TIMESTAMPTZ` columns. Naive datetimes raise `ValueError` in the builder; Postgres will silently assume UTC, so catch the error at the edge.
- **Phase-1 integration test skips the whole module if any backing store is unreachable.** Use `ENV=ci` (or ensure the stack is up) to force it to run. Do not change the skip semantics without updating the CI gate.

**Phase 1 / live validation (2026-04-22)**
- **Local Neo4j vs compose Neo4j collide on host port 7687.** Always run one at a time: `brew services stop neo4j` (or quit Neo4j Desktop) before `make up`, then `brew services start neo4j` after `make down`. `scripts/neo4j_load_phase1_local.py` will refuse to run when only the compose Neo4j is up (it reads `G_DB_*` from `.cursor/.env`, which points at the local instance).
- **Neo4j's `NEO4J_AUTH` only takes effect on first volume initialization.** If you change `NEO4J_PASSWORD` in `.env` but the `docker_neo4j_data` volume already exists, the password is still the one from first boot and the migrator's `cypher-shell` will fail with `The client is unauthorized due to authentication failure`. Fix: `docker compose down -v` to nuke volumes, then `make up`. Encountered live on 2026-04-22 during the first `make up` after `.env` was updated to use the real Neo4j password.
- **Host-side env vars must be overridden to run the integration test off-compose-network.** `civic_common.Settings` reads `NEO4J_URI`, `POSTGRES_HOST`, `OPENSEARCH_URL`, `MINIO_ENDPOINT` verbatim — these default to compose DNS names (`neo4j:7687`, `postgres`, …). When running `pytest` on the host, export each to its `localhost` variant for the duration of the test command. The smoke suite has a separate `*_HOST` escape hatch in `tests/smoke/conftest.py`, but the integration test does NOT — it goes through `civic_clients` which goes through `Settings`.
- **`!` in `NEO4J_PASSWORD` triggers zsh history expansion.** Wrap the var in a `bash -c '...'` block when exporting, or double-quote it as `"Polazin2!"` inside a bash subshell. Plain zsh `export NEO4J_PASSWORD=Polazin2!` will blow up with `command not found: NEO4J_PASSWORD=Polazin2`.
- **Third-party Jupyter kernels on macOS often grab ports 9000 / 9001 on loopback.** This blocks the MinIO compose container from binding. Check with `lsof -nP -iTCP:9000 -iTCP:9001 -sTCP:LISTEN` before `make up` and kill the offending pid if it's unrelated to this project (we hit this once during the 2026-04-22 validation).
- **Neo4j 5's `CALL { ... } IN TRANSACTIONS` emits a deprecation warning about missing variable scope clause.** The current form (`CALL { MATCH (n) DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS`) still works — the warning is `gql_status=01N00`. Future 5.x/6.x may drop support; the fix when that happens is `CALL () { ... }` per the warning text.
- **The API image MUST `uv sync` against the workspace, not `uv pip install <flat list>`.** `apps/api/src/api/clients/*` re-exports `civic_clients.*` and `api/settings.py` re-exports `civic_common.settings` — both workspace packages. A flat `uv pip install fastapi pydantic …` leaves them uninstalled and the container exits 1 on import. `apps/api/Dockerfile` now does a two-layer build: COPY `uv.lock` + every workspace `pyproject.toml` → `uv sync --package civic-api --frozen --no-dev --no-install-project` (cached deps layer) → COPY `packages/common`, `packages/clients`, `apps/api` → `uv sync --package civic-api --frozen --no-dev`. Venv lives at `/app/.venv`; `PATH` picks up `uvicorn`. The dev override mounts `apps/api/src` into `/app/apps/api/src` (not `/app/src`) to match the new workspace layout. Worker and migrator images are unaffected — worker's `main.py` only imports `structlog` + local `.settings`, migrator runs bash + `alembic` + `cypher-shell`. If `uv sync --frozen` starts failing in the build, the right fix is to refresh `uv.lock`, NOT to drop `--frozen`.

### Phase-2 / ingestion decisions (2026-04-23)
- **Real-data tests everywhere, forever.** As of the 2026-04-23 re-run, `tests/fixtures/**` contains ONLY byte-for-byte recordings of real upstream responses and Pydantic-shaped projections of them. Hand-crafted domain entities are forbidden repo-wide — enforced by `.cursor/rules/real-data-tests.mdc` (`alwaysApply: true`) and by `tests/smoke/test_alignment.py::test_no_synthetic_placeholders_in_fixtures`. Every cassette directory carries a `SOURCE.md` (URL / capture date / SHA-256 / truncation); the alignment audit fails the build if it's missing. Re-recording is a single `make record-cassettes` call backed by `scripts/record-cassettes.sh`; never hand-edit a cassette. See ADR-0002 "2026-04-23 policy strengthening" and `.cursor/rules/real-data-tests.mdc` for the full policy.
- **HTTP fetch mode is VCR record/replay.** Live-ish recording happens once per URL via `python -m civic_archival fetch --out <path>` (batch via `make record-cassettes`). Unit tests load the resulting real-byte cassettes directly; the integration tests (`tests/integration/test_phase2_ingestion.py` + `tests/integration/test_phase1_persistence.py`) replay them through a stub fetcher, so the whole pipeline is reproducible offline while still exercising real payload shapes. The votes adapter uses a CSV cassette from `production.oknesset.org/pipelines/data/votes/` because the official Knesset per-MK vote OData endpoint is bot-protected.
- **Job queue is Postgres-native (`SELECT … FOR UPDATE SKIP LOCKED`).** No Redis, no RabbitMQ, no Celery — the `jobs` table + the CTE-based claim in `civic_ingest.queue.claim_one` is enough for Phase-2's throughput envelope (one worker tick = one claim). Dead-letter policy: `attempts >= max_attempts` (default 5) flips the row to `dead_letter` and freezes `run_after`, so failed jobs are visible but un-claimable. Exponential backoff is `attempts * attempts` seconds (1, 4, 9, 16, 25) — intentionally gentle to tolerate flaky upstream OData.
- **Deterministic UUIDs are `uuid5(PHASE2_UUID_NAMESPACE, "knesset_<kind>:<external_id>")`.** `PHASE2_UUID_NAMESPACE = 00000000-0000-4000-8000-00000000beef`. Every adapter uses the same namespace + the same `<kind>` prefixes (`knesset_person`, `knesset_party`, `knesset_office`, `knesset_committee`, `knesset_bill`, `knesset_vote`, `knesset_attendance_event`, `knesset_membership_term`). Re-running any adapter on the same OData row produces the same UUID, which is what makes the Phase-1 `MERGE` templates idempotent across runs.
- **Adapter scope is "Knesset 25 full coverage".** Manifests point at `https://knesset.gov.il/OdataV4/ParliamentInfo.svc/…` but the real pagination story (first-page vs. `$filter=KnessetNum eq 25`) is deferred to the first live recording session. Cadences (`cadence_cron`) are configured but no scheduler runs them yet — the worker currently drains whatever the ingest CLI enqueues.
- **Entity resolution is deterministic-only for Phase 2.** Steps 1-4 of the plan's six-step ladder are implemented; step 5 (fuzzy matching on Hebrew names) and step 6 (LLM fallback with rules-only fact evaluation) are explicitly deferred. The `entity_aliases` table is empty at migration time — curated aliases are populated incrementally by reviewers (the review workflow in Phase 5 will own the write path).
- **`IngestRun` + `run_adapter` take a `psycopg.Connection` and hold the same transaction across archive + worker-stats writes.** `archive_payload(conn=run.connection)` participates in the outer transaction; the outer `IngestRun.__exit__` commits only if no exception propagates. Individual Neo4j upserts happen outside the Postgres transaction (Neo4j has its own commit story) — if a Neo4j upsert fails after the `raw_fetch_objects` row is committed, the row stays (archival is cheap; re-running the same payload hits the `content_sha256` UNIQUE constraint and returns `created=False`).
- **`civic_ingest.handlers` registry is the dispatch seam.** Adapters register their own handlers (`@handlers.register("fetch", adapter="people")`) at import time; the worker calls `handlers.dispatch(job)` without needing to know which adapters exist. Adapter-specific handlers win over default handlers for the same kind. Phase 2 currently ships the registry skeleton + the direct-CLI path; the worker's live loop wires into this in the next live-validation pass.

### Known gotchas (Phase 2)
- **`tests/*/test_*.py` filenames must be unique across workspace members.** Pytest's rootdir collection imports modules by basename, and when every adapter ships a `tests/test_parse_normalize.py` the second one to collect raises `ImportPathMismatchError`. We renamed them to `test_people.py`, `test_committees.py`, `test_votes.py`, `test_sponsorships.py`, `test_attendance.py`. Do NOT add `__init__.py` to `services/*/tests/` or `services/ingestion/knesset/*/tests/` — same reason as the Phase-1 gotcha about `packages/*/tests/`.
- **`apps/worker/src/worker/main.py` falls back to the Phase-0 stub path when Postgres is unreachable.** This is deliberate: the worker smoke test `test_run_once_returns_ok` asserts `{"env":"dev","ok":True}`, and we preserve that contract. Production boots with Postgres reachable, so the live path (claim one job, dispatch, commit) runs; unit tests exercise the stub path. If the worker starts returning the wrong status dict, first check whether the sibling `conftest` is leaking a non-dev `ENV` (Wave-A A5 fix).
- **`uv sync --all-packages` (not plain `uv sync`) is required** after adding workspace members. `uv sync` only syncs the root's direct dependency graph, not every workspace pyproject. If `ModuleNotFoundError: civic_archival` appears after a fresh clone, re-run `uv sync --all-packages`.
- **The Phase-1 `entity_candidates` schema is person-scoped** (`resolved_person_id`, `mention_text`). The resolver only writes there for `kind="person"`; ambiguous matches for `party`/`office`/`committee`/`bill` are returned to the caller as `ResolveResult(status="ambiguous")` but not persisted. Phase-3 must extend the schema (add `entity_kind` + rename `resolved_person_id` to a polymorphic `canonical_entity_id`) before the review UI can queue non-person ambiguous cases.
- **`uuid5` namespace must not change.** If `PHASE2_UUID_NAMESPACE` ever drifts (e.g. refactored to a different constant), every previously upserted node becomes orphaned — the `MERGE`-on-business-key logic will create duplicates. Treat it as a stable key forever.
- **AttendanceEvent `ATTENDED` edge landed in Phase 3 / wired end-to-end in Phase 2.5.** Phase-2's original B5 adapter left attendees empty (no `attended.cypher` template existed). Phase-3 A7 added the relationship template; Phase-2.5 then switched the adapter source from Tier-1 OData (which has no attendees) to the Tier-2 oknesset CSV (which does) and populated the edge. See the Phase-2.5 milestone for the full attendance rewrite.
- **`KNS_Vote.Vote` value mapping is permissive.** Hebrew (`בעד`/`נגד`/`נמנע`), English (`for`/`against`/`abstain`), and integers (1/2/3) all map; anything else is silently dropped. The `CAST_VOTE` template has a `WHERE value IN ['for','against','abstain']` guard, so an unmapped value would be dropped there anyway — we drop earlier for observability. If upstream introduces a new code, add it to `_KNS_VOTE_VALUE` in `services/ingestion/knesset/votes/src/civic_ingest_votes/normalize.py`.
- **`UPSERT_ROOT` / `REPO_ROOT` in every adapter is `Path(__file__).resolve().parents[6]`.** Adapter source at `services/ingestion/knesset/<name>/src/civic_ingest_<name>/{upsert,cli}.py` walks up through `civic_ingest_<name>/src/<name>/knesset/ingestion/services/` so `parents[6]` is the repo root. Earlier code said `parents[5]` (= `services/`), which made `UPSERT_ROOT` point at a nonexistent `services/infra/neo4j/upserts/` — bug was masked while the Phase-2 integration test ran against synthetic cassettes. The 2026-04-23 real-data run surfaced and fixed it across all five adapters' `upsert.py` and `cli.py`.
- **`Person.external_ids` is a JSON string on the Neo4j side.** `infra/neo4j/upserts/person_upsert.cypher` takes `$external_ids` as a JSON-encoded string (not a Map) because Neo4j properties must be primitive types or arrays thereof. `civic_ingest_people.upsert_person` serializes with `json.dumps(person.external_ids, ensure_ascii=False)` before passing; `tests/integration/test_phase1_persistence.py::_person_params` does the same. Do not pass a raw dict — it will raise `Neo.ClientError.Statement.TypeError`. Cypher queries use `p.external_ids CONTAINS '"knesset_person_id"'` (substring match on the serialized form).
- **The votes upsert MERGEs a stub `Person` before each `CAST_VOTE` edge.** The oknesset vote CSV may reference MKs from different Knesset terms than whatever subset the people adapter has ingested so far, so the edge's Person endpoint may not yet exist when votes run first. `upsert_vote` issues a `MERGE (:Person {person_id: …})` with `canonical_name=None` etc., so the People pipeline can back-fill canonical attributes later (via `coalesce($x, p.x)`). Removing the stub silently drops every CAST_VOTE edge because `cast_vote.cypher` `MATCH`es both endpoints. **The back-fill requires the People cassette to actually contain the MK** — the 2026-04-23 "Historical MK coverage" fix dropped the `IsCurrent eq true` filter from the People manifest for exactly this reason; with the filter on, every vote-stub Person stayed nameless forever because current-term MKs are a strict subset of the vote CSV's historical referents.
- **Stub Person nodes carry `source_tier=2`; don't mistake it for a person id.** The votes adapter's pre-edge stub has `person_id=<uuid>`, `canonical_name=None`, `hebrew_name=None`, `external_ids=None`, `source_tier=2` — so the only scalar property legibly returned by most Neo4j Browser queries is `source_tier=2`. That's the Tier-2 provenance (oknesset CSV mirror), not an id. On the next People pass (Tier-1 KNS_Person), `source_tier` is upgraded to `1` via `coalesce()` and `canonical_name` / `hebrew_name` / `external_ids` get populated.
- **`raw_fetch_objects` is content-addressed and globally dedup'd.** `archive_payload()` checks for an existing row by `content_sha256` and returns `created=False` if found, reusing the prior `ingest_run_id` rather than linking the new run. Integration tests MUST assert on `content_sha256` presence, not on `COUNT(*) WHERE ingest_run_id = …`, to stay rerun-safe. `tests/integration/test_phase2_ingestion.py::test_phase2_ingestion_roundtrip` collects the five expected hashes from the adapter loop and asserts `COUNT(*) WHERE content_sha256 = ANY(<hashes>) = 5`.

### Phase-2.5 / join adapters decisions (2026-04-23)
- **Split committee memberships into a dedicated adapter, not a third lane of `positions`.** The original plan proposal envisaged `positions` handling `MEMBER_OF` + `HELD_OFFICE` + `MEMBER_OF_COMMITTEE` as three lanes keyed on `FactionID` / `PositionID` / `CommitteeID`. Real-data inspection showed `CommitteeID` is populated on 0 of 11,090 rows in `KNS_PersonToPosition` — the field is declared in the OData schema but never filled. Committee memberships are only published through the oknesset Tier-2 mirror (`mk_individual_committees.csv`), which keys on `mk_individual_id` (not `PersonID`) and has its own temporal bounds. So a fourth Phase-2.5 adapter was added rather than stretching `positions` across two tiers + two keying schemes.
- **Shared `MkIndividualLookup` lives in `civic_ingest._common`, not duplicated per adapter.** Two adapters (`committee_memberships`, `attendance`) need the same `mk_individual_id` → `PersonID` map. The lookup parses `mk_individual.csv` (~240 KB) once per process via `@lru_cache(maxsize=1)` on the default-path loader. Production CLIs call `load_mk_individual_lookup(fetched_bytes)` to bypass the cache and pick up fresh data on every run.
- **`mk_individual.csv` is filed under `tests/fixtures/phase2/lookups/`, not `cassettes/`.** The `cassettes/` directory is reserved for recordings that adapters ingest; `mk_individual.csv` is consumed by adapters as a dimension table but never upserted into the graph itself. The `lookups/` subtree has its own `SOURCE.md` template; `scripts/record-cassettes.sh` writes both.
- **Every Phase-2.5 relationship adapter MERGEs stub endpoints before the edge.** `positions` upserts stub `Person` → `Party` → `MEMBER_OF` → `Office` → `HELD_OFFICE` (5 calls per full bundle). `bill_initiators` upserts stub `Person` → stub `Bill` → `SPONSORED`. `committee_memberships` upserts stub `Person` → stub `Committee` → `MEMBER_OF_COMMITTEE`. `attendance` upserts stub `Person` → `ATTENDED` (the `AttendanceEvent` already exists from the session-level pass earlier in the same adapter). All stubs have `canonical_name=None` etc. so the dimension-owner adapter (`people` / `sponsorships` / `committees`) back-fills via `coalesce()` on a later pass. This is the same pattern as the Phase-2 votes adapter — not a new invention.
- **Office UUIDs are composite on `(PositionID, GovMinistryID)`.** `uuid5(PHASE2_UUID_NAMESPACE, f"knesset_office:{PositionID}:{GovMinistryID or '-'}")`. Two MKs who both hold `PositionID=55` (minister) at different ministries get distinct Office nodes — which is what we want, because "Minister of Defense" and "Minister of Education" are different offices. A GovMinistryID of `None` collapses to the literal `"-"` so generic ministerial roles stay deterministic.
- **`bill_initiators` filters `IsInitiator=True` at the parse layer.** `KNS_BillInitiator` rows come in two flavors: primary initiators (`IsInitiator=True`) and co-signatories (`IsInitiator=False`). V1 only emits SPONSORED edges for primary initiators — co-signatories are a Phase-3+ feature once the ontology distinguishes the two. `parse.py` drops the False rows so `normalize.py` never sees them; a future change to include co-signatories is a two-line edit plus a new `SPONSORED` edge property (e.g. `sponsorship_kind`).
- **Attendance is hardcoded to `presence="present"` for v1.** The oknesset `attended_mk_individual_ids` column is a list of attendees — absentee rows don't exist. If an MK was absent from a session, their `PersonID` simply doesn't appear in the list; we emit no ATTENDED edge at all rather than synthesizing an `absent` edge. The `attended.cypher` template accepts `presence` so future sources (e.g. a Tier-1 roll-call feed if one ever materializes) can populate `absent` / `excused` directly.

### Known gotchas (Phase 2.5)
- **`KNS_PersonToPosition.CommitteeID` is declared but never populated.** 0 of 11,090 rows (April 2026). The OData schema emits the column in every row as `null`. Do not treat this as a transient data-quality bug — the upstream pipeline simply doesn't populate it. Use the `committee_memberships` adapter (oknesset Tier-2) for committee edges.
- **`KNS_BillInitiator` does not support `$filter=KnessetNum eq 25`.** The column isn't in the OData model and the endpoint returns HTTP 400. The cassette recorder instead uses `$orderby=BillInitiatorID desc&$top=100` — the 100 most recent rows, which are reliably current Knesset bills. If you need a specific Knesset's bills, filter post-hoc in `parse.py` by joining against `KNS_Bill.KnessetNum`.
- **`attended_mk_individual_ids` in `kns_committeesession.csv` is a Python literal, not JSON.** The column contains strings like `"[1234, 5678, 91011]"` — Python-list syntax (space after comma is inconsistent, sometimes quoted as strings). `parse_attendance` uses `ast.literal_eval` to parse it, NOT `json.loads`. Do not switch to JSON parsing without re-recording the cassette first to verify the on-disk shape.
- **Early rows of `kns_committeesession.csv` have empty `attended_mk_individual_ids`.** The cassette must cover at least one row with a populated attendee list or the adapter's idempotency test becomes a no-op. Record with `--max-lines 51` (not the smaller value that works for other adapters) — the first ~30 rows frequently have empty attendee arrays.
- **`mk_individual_id` is NOT `PersonID`.** Two separate identifier spaces: `mk_individual_id` is an oknesset-local PK (auto-incrementing int), `PersonID` is the canonical Knesset-ParliamentInfo identifier. The `mk_individual.csv` dimension table publishes both on every row and is the sole join key. Do not hard-code any `mk_individual_id` values in code or tests — they drift every time oknesset rebuilds their pipeline.
- **Always extend `AdapterKind` AND `source_manifest.schema.json` together.** Adding a new adapter is a four-file change: (1) adapter package `pyproject.toml` + source, (2) `services/ingestion/_common/src/civic_ingest/manifest.py` `AdapterKind` Literal, (3) `data_contracts/jsonschemas/source_manifest.schema.json` `adapter` enum, (4) `tests/smoke/test_alignment.py` `PHASE2_ADAPTERS` list. The Pydantic + JSON Schema pair stays in sync by convention, not automation — alignment audit would NOT catch a mismatch between them, only a mismatch between `PHASE2_ADAPTERS` and the manifest files on disk.
- **`apps/api/Dockerfile` MUST be extended when adding a workspace member.** Same rule as Phase 3/4: `uv sync --frozen --package civic-api` builds every member declared in `[tool.uv.workspace].members`, regardless of whether it's in the api's dep graph. Missing `COPY` line → `Distribution not found at: file:///app/services/ingestion/knesset/<new>`. Fix: add `COPY services/ingestion/knesset/<new> services/ingestion/knesset/<new>` alongside the existing service copies.
- **Phase-2.5 adapter unit tests use the shared `MkIndividualLookup` default fixture by default.** `load_mk_individual_lookup(source=None)` resolves to `tests/fixtures/phase2/lookups/mk_individual/sample.csv` via `Path(__file__).resolve().parents[5]`. If the service package layout ever changes, recount parents — the test suite will fail with a cryptic `FileNotFoundError` during collection, not a friendly assertion error.

### Phase-3 / atomic claim pipeline decisions (2026-04-23)
- **Rules-first decomposition, LLM fallback behind schema validation.** `civic_claim_decomp.decompose(statement, language)` runs Hebrew/English regex templates first (`civic_claim_decomp.rules.RULE_TEMPLATES`); when nothing matches and a provider was wired, it calls the `LLMProvider` protocol. Both paths run through `civic_ontology.claim_slots.validate_slots` before a `DecomposedClaim` is emitted — the LLM can never produce an unvalidated claim. The six supported claim types are `vote_cast`, `bill_sponsorship`, `office_held`, `committee_membership`, `committee_attendance`, `statement_about_formal_action`; each has a `SlotTemplate` pinning required/optional/forbidden slots and the drift check in `civic_ontology.schemas.check_schemas` asserts 1:1 coverage against the `ClaimType` enum.
- **Temporal normalizer is deterministic and language-aware.** `civic_temporal.normalize_time_scope(phrase, *, language, reference_date=None)` handles ISO dates, year-only phrases, Hebrew month names, Knesset-term references (`"הכנסת ה-25"` / `"25th Knesset"`), `"last year"` / `"בשנה שעברה"`, and `"last term"` / `"הקדנציה הקודמת"`. The list of Knesset terms (`civic_temporal.KNESSET_TERMS`) is version-pinned; adding a new term is a single-file edit. Unknown phrases return `TimeScope(start=None, end=None, granularity="unknown")` — never raises.
- **Checkability classifier runs after both the slot validator AND the resolver.** `civic_claim_decomp.checkability.classify(CheckabilityInputs(...))` returns one of `non_checkable`, `insufficient_entity_resolution`, `insufficient_time_scope`, `checkable`. `vote_cast` and `committee_attendance` REQUIRE a non-`unknown` time granularity; the other four claim types tolerate unknown time. A slot whose resolver status is `ambiguous` / `unresolved` blocks checkability even if the slot value is non-empty.
- **Entity resolution v2 adds fuzzy + LLM tiebreaker.** `services/entity_resolution/src/civic_entity_resolution/resolver.py` now implements all six ladder steps: alias lookup, exact Hebrew, exact English, external-id crosswalk, rapidfuzz fuzzy (token-set ratio, `FUZZY_RESOLVE_THRESHOLD=92`, `FUZZY_MARGIN=5`), and an optional `LLMEntityTiebreaker` protocol for step 6. Migration `0005_polymorphic_entity_candidates.py` renamed `resolved_person_id` → `canonical_entity_id` and added `entity_kind` so non-person entities can be queued; the resolver now writes `entity_candidates` rows for all kinds, not just persons.
- **Graph edges for Phase-3 claim types.** Added `infra/neo4j/upserts/relationships/attended.cypher` (`(:Person)-[:ATTENDED {presence}]->(:AttendanceEvent)`), bringing relationship count to 12. The attendance ingest adapter (`civic_ingest_attendance.upsert`) now creates the ATTENDED edge for every attendee of an `AttendanceEvent`, not just the event node.
- **Statement intake persistence.** Migration `0006_statements.py` adds two Postgres tables: `statements` (raw input body + language + optional speaker hint) and `statement_claims` (one row per decomposed atomic claim, FK to `statements.id`). `civic_claim_decomp.persistence.persist_statement(conn, StatementRecord)` inserts both in a single transaction so partial writes are impossible.
- **Real-data gold set for evaluation.** `scripts/record-statements.py` fetches a statement URL, extracts an excerpt (optional CSS selector), and writes `tests/fixtures/phase3/statements/<slug>/{statement.txt, SOURCE.md, labels.yaml}`. The real-data-tests policy (`.cursor/rules/real-data-tests.mdc`) forbids hand-invented statements, and `tests/smoke/test_alignment.py::test_gold_set_statements_have_pinned_labels` asserts every statement folder ships the three required files.

### Phase-4 / retrieval + verdict decisions (2026-04-23)
- **Three-layer retrieval.** `civic_retrieval.graph.GraphRetriever` loads a Cypher template per claim_type from `infra/neo4j/retrieval/*.cypher` (six templates total — one per claim type) and returns typed `GraphEvidence` records. `civic_retrieval.lexical.LexicalRetriever` issues BM25 + optional kNN queries against the `evidence_spans` OpenSearch index and returns `LexicalEvidence`. OpenSearch template `0002_evidence_spans.json` now declares both `normalized_text` (BM25) and `embedding` (`knn_vector`, dimension 384).
- **Deterministic reranker, no learned model in v1.** `civic_retrieval.rerank.rerank(...)` combines five signals with fixed weights (`WEIGHTS` is the single source of truth consumed by both the reranker and the verification rubric): `source_tier` (0.30), `directness` (0.25), `temporal_alignment` (0.20), `entity_resolution` (0.15), `cross_source_consistency` (0.10). A `RerankScore` always carries the unweighted axis scores so the verdict engine can build the Confidence vector without re-scanning evidence.
- **Verdict engine is purely rule-driven.** `civic_verification.decide_verdict(VerdictInputs)` maps `(claim_type, ranked_evidence, checkability)` to one of the five verdict statuses from the `Verdict` ontology model. `vote_cast` contradicts whenever the recorded `vote_value` mismatches `expected_vote_value`; `committee_attendance` contradicts when every matching `AttendanceEvent` has `presence='absent'`; `statement_about_formal_action` needs ≥2 lexical corroborations to `support`, 1 → `mixed`, 0 → `insufficient_evidence`. No LLM is involved anywhere in the decision path.
- **Abstention thresholds live in code, not config.** `ABSTAIN_OVERALL = 0.45` (below this we return `insufficient_evidence`) and `HUMAN_REVIEW_OVERALL = 0.62` (below this we still set `needs_human_review=True` on any support/contradict outcome). Changing a threshold is a one-commit PR with a matching test update — intentionally high-friction.
- **Five-axis confidence rubric shares weights with the reranker.** `civic_verification.compute_confidence(ranked)` takes the MAX across evidence for directness / temporal / entity / cross-source and the MAX `source_tier` score, then computes `overall` using `civic_retrieval.rerank.WEIGHTS`. Ops docs therefore only need to point at one constant to explain axis importance.
- **Provenance bundler is the API wire shape.** `civic_verification.bundle_provenance(outcome, ranked, ...)` returns a `ProvenanceBundle` with `verdict`, `top_evidence` (default top-5), and `uncertainty_note`. The `EvidenceSummarizer` protocol is the ONLY LLM seam in verification — it drafts the reviewer-facing `uncertainty_note` paragraph and can never alter verdict fields. Summarizer failures are swallowed; the bundle still returns.
- **`/claims/verify` API composes the full Wave-1 + Wave-2 pipeline.** `apps/api/src/api/routers/claims.py` is a thin route that delegates to `api.routers.pipeline.VerifyPipeline`; tests override `get_pipeline` to inject deterministic fake graph/lexical retrievers. The default pipeline has no backends wired, so the route is always reachable; with empty evidence the verdict engine abstains with `insufficient_evidence` by design.
- **Review workflow MVP.** `civic_review.PostgresReviewRepository` implements `list_open_tasks` + `resolve_task` inside a single transaction (task UPDATE + `review_actions` INSERT). The five audit actions (`approve`, `reject`, `relink`, `annotate`, `escalate`) match the Phase-1 CHECK constraint; `annotate` is non-terminal (keeps the task `open`), the others close it. Terminal tasks still record an audit trail for any attempted follow-up action — no silent no-ops.
- **~40 new alignment-audit rows.** `tests/smoke/test_alignment.py` now pins: every claim_type has a slot template + graph retrieval template, reranker exposes all five weighted signals, `evidence_spans` mapping declares BM25 + knn_vector, verification module exposes engine + rubric, abstention thresholds are named constants, API main wires all three routers, API pyproject declares every pipeline dep, prompt loader exposes `load_card`, migrations 0005/0006 create the expected tables, entity resolver exposes fuzzy + tiebreaker symbols, gold-set folders ship `statement.txt + SOURCE.md + labels.yaml`. Total Phase-3/4 alignment row count: 40 (parametrized) + 12 singleton tests.

### Known gotchas (Phase 3 + 4)
- **`infra/neo4j/retrieval/<claim_type>.cypher` is resolved via `Path(__file__).resolve().parents[4]`.** The retriever lives at `services/retrieval/src/civic_retrieval/graph.py`, so `parents[4]` is the repo root. Earlier draft used `parents[5]` and yielded `/Users/idan/projects/infra/...` (off by one). When moving the module, recount parents before merging.
- **FastAPI can't introspect `VerifyPipeline | None` or any Protocol-typed dataclass field in a `Depends(...)`.** The router uses `Annotated[VerifyPipeline, Depends(get_pipeline)]` instead of the bare default-argument form; test fakes return a pre-instantiated `_Stub()` wrapped in a lambda rather than a subclass, because FastAPI otherwise walks the dataclass fields as request/response model hints and crashes on the Protocol annotations.
- **`packages/prompts` needs `[tool.hatch.build.targets.wheel.force-include]`** for every YAML category (`decomposition`, `temporal_normalization`, `summarize_evidence`, `reviewer_explanation`). Without the `force-include` block the YAML files are present in source but missing from the wheel, which silently breaks `civic_prompts.load_card` at runtime. The `shared-data` config key looks correct but maps to a different install location.
- **Workspace `uv sync` fails fast if a registered member is missing `pyproject.toml`.** When scaffolding new service packages (`services/normalization`, `services/retrieval`, `services/verification`, `services/review`), add the pyproject + `__init__.py` together — the "add to `[tool.uv.workspace].members` first, create files later" pattern will blow up the workspace resolver for every follow-up `uv` command.
- **`tests/integration/conftest.py` must set the env vars at collection time.** `api.main` instantiates `Settings()` at import, and the `apps/api/tests/conftest.py` block only runs for API tests. Phase-3+4 integration tests import `api.main`, so `tests/integration/conftest.py` replicates the `os.environ.setdefault(...)` block from `apps/api/tests/conftest.py`.
- **`integration` marker needs to stay in the workspace `[tool.pytest.ini_options]`.** Phase-1 audit (Wave-2) registered the marker; do not drop it when adding Phase-3+4 integration tests or the suite reemits `PytestUnknownMarkWarning`.
- **Review actions vs. verdict statuses are DIFFERENT vocabularies.** The API accepts `decision ∈ {approve, reject, relink, annotate, escalate}` (audit-log action, per migration 0002 CHECK constraint), while the verdict engine emits `status ∈ {supported, contradicted, mixed, insufficient_evidence, non_checkable}`. Don't conflate them in payloads or reviewer UI state.
- **`apps/api/Dockerfile` must COPY every workspace member's source, not just the api's direct deps.** (2026-04-23) The Phase-3/4 `civic-api` pyproject now depends on `civic-claim-decomp`, `civic-temporal` (in `services/normalization`), `civic-retrieval`, `civic-verification`, `civic-entity-resolution`, `civic-review`, and transitively on `civic-prompts` — all workspace members. `uv sync --frozen` parses EVERY declared member in `[tool.uv.workspace].members` (not just the target package's graph) and fails with `Distribution not found at: file:///app/<member>` if any member's `pyproject.toml` is missing from the build context; it ALSO builds every workspace member whose dist is required transitively, which means their full source trees must be present too (not just their pyproject). `civic-prompts` in particular has `[tool.hatch.build.targets.wheel.force-include]` pointing at `src/civic_prompts/<category>` directories, so the COPY must be the whole `packages/prompts/` tree, not just the manifest. The previous two-layer split (COPY pyproject.tomls → `uv sync --no-install-project` → COPY source → `uv sync`) was collapsed into a single-layer build because `--no-install-project` only skips the root project, not workspace siblings, so the split wasn't actually caching anything once any workspace dep had a non-trivial build config. If `uv sync --frozen` fails in the image build after adding a new workspace member, the fix is to add `COPY <member_path> <member_path>` to `apps/api/Dockerfile` — NOT to drop `--frozen` or `--package`.

### Performance baselines
_(append after first eval run)_
