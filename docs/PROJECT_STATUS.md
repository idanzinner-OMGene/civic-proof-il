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

_No active phases — Phase 2 scaffold + first ingestion family landed 2026-04-23 (unit tests only; live-stack integration run pending)._

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
- `tests/fixtures/phase2/cassettes/people/sample.json` — `KNS_Person?$filter=IsCurrent eq true&$top=…` from `knesset.gov.il/Odata/ParliamentInfo.svc/`.
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

---

## Remaining pipeline — priority order

| # | Phase | Description | Priority |
|---|-------|-------------|----------|
| 1 | Phase 2 live validation | `make up` → `make migrate` (0003 + 0004) → run `tests/integration/test_phase2_ingestion.py` end-to-end; record a real VCR cassette set via `make record-cassettes` (to be scripted) | high |
| 2 | Phase 3 — Atomic claim pipeline | Statement intake API, rule-first decomposition, ontology mapper, temporal normalizer, checkability classifier | high |
| 3 | Phase 4 — Retrieval + verification | Graph retrieval, lexical+vector retrieval, deterministic reranker, verdict engine, abstention policy, provenance bundle | high |
| 4 | Phase 5 — Review workflow | Reviewer queue, conflict queue, entity-resolution correction, verdict override with audit log | medium |
| 5 | Phase 6 — Hardening + evaluation | Benchmark set, offline eval harness, regression tests, provenance completeness tests, freshness monitoring | medium |

Acceptance criteria and detailed deliverables for each phase are in [political_verifier_v_1_plan.md](political_verifier_v_1_plan.md).

> Phase 0 and Phase 1 moved to Completed milestones on 2026-04-21.

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
- **AttendanceEvent nodes don't yet have an `ATTENDED` relationship template.** Phase-2's B5 adapter captures attendee person UUIDs on the normalized bundle but only upserts the node — Phase-3 must add `infra/neo4j/upserts/relationships/attended.cypher` and wire it into `civic_ingest_attendance.upsert`.
- **`KNS_Vote.Vote` value mapping is permissive.** Hebrew (`בעד`/`נגד`/`נמנע`), English (`for`/`against`/`abstain`), and integers (1/2/3) all map; anything else is silently dropped. The `CAST_VOTE` template has a `WHERE value IN ['for','against','abstain']` guard, so an unmapped value would be dropped there anyway — we drop earlier for observability. If upstream introduces a new code, add it to `_KNS_VOTE_VALUE` in `services/ingestion/knesset/votes/src/civic_ingest_votes/normalize.py`.
- **`UPSERT_ROOT` / `REPO_ROOT` in every adapter is `Path(__file__).resolve().parents[6]`.** Adapter source at `services/ingestion/knesset/<name>/src/civic_ingest_<name>/{upsert,cli}.py` walks up through `civic_ingest_<name>/src/<name>/knesset/ingestion/services/` so `parents[6]` is the repo root. Earlier code said `parents[5]` (= `services/`), which made `UPSERT_ROOT` point at a nonexistent `services/infra/neo4j/upserts/` — bug was masked while the Phase-2 integration test ran against synthetic cassettes. The 2026-04-23 real-data run surfaced and fixed it across all five adapters' `upsert.py` and `cli.py`.
- **`Person.external_ids` is a JSON string on the Neo4j side.** `infra/neo4j/upserts/person_upsert.cypher` takes `$external_ids` as a JSON-encoded string (not a Map) because Neo4j properties must be primitive types or arrays thereof. `civic_ingest_people.upsert_person` serializes with `json.dumps(person.external_ids, ensure_ascii=False)` before passing; `tests/integration/test_phase1_persistence.py::_person_params` does the same. Do not pass a raw dict — it will raise `Neo.ClientError.Statement.TypeError`. Cypher queries use `p.external_ids CONTAINS '"knesset_person_id"'` (substring match on the serialized form).
- **The votes upsert MERGEs a stub `Person` before each `CAST_VOTE` edge.** The oknesset vote CSV covers different Knesset terms than the `KNS_Person` OData cassette we pin for the people adapter, so the edge's Person endpoint may not yet exist when votes run first. `upsert_vote` issues a `MERGE (:Person {person_id: …})` with `canonical_name=None` etc., so the People pipeline can back-fill canonical attributes later (via `coalesce($x, p.x)`). Removing the stub silently drops every CAST_VOTE edge because `cast_vote.cypher` `MATCH`es both endpoints.
- **`raw_fetch_objects` is content-addressed and globally dedup'd.** `archive_payload()` checks for an existing row by `content_sha256` and returns `created=False` if found, reusing the prior `ingest_run_id` rather than linking the new run. Integration tests MUST assert on `content_sha256` presence, not on `COUNT(*) WHERE ingest_run_id = …`, to stay rerun-safe. `tests/integration/test_phase2_ingestion.py::test_phase2_ingestion_roundtrip` collects the five expected hashes from the adapter loop and asserts `COUNT(*) WHERE content_sha256 = ANY(<hashes>) = 5`.

### Performance baselines
_(append after first eval run)_
