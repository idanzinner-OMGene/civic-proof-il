# Changelog — civic-proof-il Political Verifier

> **Purpose:** Detailed implementation history moved from the former monolithic [`PROJECT_STATUS.md`](PROJECT_STATUS.md). For **current state**, **priorities**, and **where to look next**, read [`PROJECT_STATUS.md`](PROJECT_STATUS.md). For **gotchas and decisions**, read [`AGENT_GUIDE.md`](AGENT_GUIDE.md).

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

_Live `tests/smoke` host-side checks (Neo4j connectivity, readyz) still require a running Docker stack; unit + alignment are green in CI on every commit._

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

### Parallel agents wave — gold set + live wiring + Phase 5/6 (2026-04-26)

- **Gold set (25 rows):** Knesset OData `KNS_Person` pages (`$skip=0..24`) recorded into `tests/fixtures/phase3/statements/`; `labels.yaml` pins `semantic_test: false` (OData bytes are provenance, not natural-language test vectors). `scripts/record-statements.py` supports `--insecure-ssl` for MITMed TLS. Manifests: `tests/fixtures/phase3/manifests/gold_set.jsonl` and `batch_01.jsonl` (kept in sync; alignment still checks the latter file exists).
- **API live pipeline:** `apps/api` FastAPI `lifespan` injects `VerifyPipeline(graph, lexical, review_connection=conn)` and `PostgresReviewRepository` when all backing stores pass `ping` and, for `ENV=test`/`ci`, `CIVIC_LIVE_WIRING=1` is set. `GraphRetriever.retrieve` is invoked with `params=claim.slots` (keyword). `tests/integration/test_phase34_live_validation.py` (integration marker) hits `/claims/verify` when the stack is reachable.
- **Phase 5 — reviewer UI + review extensions:** `apps/reviewer_ui` (Jinja2 queue + task pages, compose port 8001). `civic_review.conflict`, `correction`, `evidence`; new routes `POST /review/tasks/{id}/relink-entity` and `.../confirm-evidence`. ADRs 0009–0010; `docs/ARCHITECTURE.md` updated.
- **Phase 6 — eval + regression + freshness:** `make eval` / `make freshness`, `tests/benchmark/*`, `tests/regression/*` (pytest marker `regression`). ADR-0011.
- **Test counts (this workspace run, no docker smoke):** 434 passed, 4 skipped. Alignment rows extended for Phase 5+6 file checks.

### Wave plan drift remediation — 2026-04-26 (session)

- **Protocol drift:** [`apps/api/src/api/routers/pipeline.py`](apps/api/src/api/routers/pipeline.py) `LexicalRetriever` Protocol now matches `civic_retrieval.LexicalRetriever.search(query_text, *, top_k=20, filters=...)`.
- **Compose alignment:** `reviewer_ui` added to `test_compose_has_all_services` in [`tests/smoke/test_alignment.py`](tests/smoke/test_alignment.py).
- **Ingest stats:** `run_adapter(..., adapter=...)` writes `stats.adapter` for per-adapter freshness joins ([`services/ingestion/_common/src/civic_ingest/adapter.py`](services/ingestion/_common/src/civic_ingest/adapter.py) + all Knesset CLIs + integration harness).
- **Freshness:** [`scripts/freshness_check.py`](scripts/freshness_check.py) joins manifests to Postgres `ingest_runs` (`stats->>'adapter'`), emits `last_run_at` / `stale` / `age_seconds` when DB is reachable.
- **Reviewer UI:** HTMX forms + `/proxy/tasks/...` POST routes proxy to the main API ([`apps/reviewer_ui`](apps/reviewer_ui)).
- **Semantic gold tranche:** [`tests/fixtures/phase3/manifests/semantic_gold_set.jsonl`](tests/fixtures/phase3/manifests/semantic_gold_set.jsonl) + six new `statements/*` dirs (Hebrew-rich OData bills/committees/people/factions) with `semantic_test: true` labels (strict `expected_claim_types` still empty until curators pin).
- **Evidence indexing:** [`scripts/index_evidence.py`](scripts/index_evidence.py) + `make index-evidence` — indexes one OpenSearch `evidence_spans` doc per Neo4j `:SourceDocument` (title text).
- **Eval harness:** [`scripts/eval.py`](scripts/eval.py) loads optional `statement_path`, computes claim-typing precision/recall + F1 + verdict F1 vs [`tests/benchmark/config.yaml`](tests/benchmark/config.yaml) gates (`f1_claim_typing` added).
- **Verdict policy:** Tier-2/3-only **contradicted** `vote_cast` outcomes now set `needs_human_review=True` ([`services/verification/src/civic_verification/engine.py`](services/verification/src/civic_verification/engine.py)).
- **Regression:** expanded [`tests/regression/test_verdict_provenance.py`](tests/regression/test_verdict_provenance.py) + Neo4j `SourceDocument.archive_uri` integration check in [`tests/regression/test_provenance_complete.py`](tests/regression/test_provenance_complete.py).

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

## Drift-fix plan completion (2026-04-26)

All 8 fixes from `fix-wave-plan-drifts_0b32e0a9.plan.md` are resolved:

- **Fix 1 (LexicalRetriever Protocol):** Already aligned — Protocol in `pipeline.py` already matched concrete class (`query_text`, `top_k`, `filters`).
- **Fix 2 (Alignment test `reviewer_ui`):** Already present in `test_compose_has_all_services`.
- **Fix 3 (freshness_check.py wiring):** Already implemented — `_fetch_last_runs()` queries `ingest_runs`, computes staleness via `2 × cadence_min_interval`, graceful fallback when Postgres unreachable.
- **Fix 4 (Reviewer UI forms):** Already implemented — HTMX forms for resolve/relink/confirm-evidence, proxy POST routes in `main.py`, tests cover all three proxy endpoints.
- **Fix 5 (NL gold set):** Expanded `semantic_gold_set.jsonl` from 6 to 20 entries. Recorded all 20 via `record-statements.py --insecure-ssl`. Now 51 total statement fixtures (25 original KNS_Person + 6 prior semantic + 20 new). All 26 semantic fixtures pinned with `semantic_test: true`, per-family stratum, and difficulty. Stratified across: vote_cast (4), bill_sponsorship (4+2), office_held (3), committee_membership (3+1), committee_attendance (3), cross-family (3+3).
- **Fix 6 (Evidence indexing):** Already implemented — `scripts/index_evidence.py` + `make index-evidence`.
- **Fix 7 (Eval harness):** `gold_set.yaml` expanded from 4 to 10 rows covering all 5 claim families. `eval.py` already computed precision/recall/F1. `config.yaml` `min_rows` gate enforced. Baselines recorded in [`PROJECT_STATUS.md`](PROJECT_STATUS.md) (Performance baselines).
- **Fix 8 (Regression tests):** Already implemented — `test_provenance_complete.py` has integration test for `archive_uri` + Neo4j `document_id`; `test_verdict_provenance.py` has tier-2 contradiction + `needs_human_review` test and positive-confidence → non-empty `top_evidence` test.

**Validation:** 190/190 alignment tests pass. 5/5 regression tests pass (1 integration test properly skipped when Neo4j unreachable). `make eval` exits 0 with all gates passing.
