# Project Status — civic-proof-il Political Verifier

> **Single source of truth** for current state, priorities, and baselines. **Implementation history** → [`CHANGELOG.md`](CHANGELOG.md). **Decisions, pitfalls, invariants** → [`AGENT_GUIDE.md`](AGENT_GUIDE.md).  
> Agents: read this file **before and after** substantive work; append short session notes to [Agent scratchpad](#agent-scratchpad).

---

## Current state (read this first)

- **Product:** Knowledge-graph-backed verifier for Israeli national political statements — decompose → resolve → retrieve (Neo4j + OpenSearch) → deterministic verdict + review queue. Spec: [`political_verifier_v_1_plan.md`](political_verifier_v_1_plan.md).
- **Phases 0–6 (v1 scaffold):** Delivered — monorepo, canonical model, Knesset ingestion (8 adapters + real-data cassettes), join adapters (2.5), claim pipeline, retrieval + verdict API, reviewer UI, eval / regression / freshness harness. See [Completed milestones](#completed-milestones-summary) and [`CHANGELOG.md`](CHANGELOG.md).
- **Stack:** `make up` — Postgres 16, Neo4j 5 Community, OpenSearch 2, MinIO, migrator, API, worker, reviewer UI (port 8001). Host-side integration tests need explicit env overrides to `localhost` (see [`AGENT_GUIDE.md`](AGENT_GUIDE.md)).
- **Tests:** Workspace run (no Docker smoke): **652 passed, 0 skipped** (last run, 2026-05-03). **238/238** alignment smoke rows; **5/5** regression. **`make eval`** exits 0 with current gates.
- **Live graph:** **188,431 nodes**, **1,700,701 relationships** (full Knesset ingest, 2026-05-02). Run `make ingest` to refresh (requires `make up`).
- **Live wiring in tests:** For API integration against real backends, set **`CIVIC_LIVE_WIRING=1`** with `ENV=test` or `ci` so lifespan mounts graph + lexical retrievers (see [`AGENT_GUIDE.md`](AGENT_GUIDE.md)).

---

## Next priorities

**v1 is fully shipped.** Active work is on v2.

V2 plan: [`V2_IMPLEMENTATION_PLAN.md`](V2_IMPLEMENTATION_PLAN.md).

| V2 PR | Status | Description |
|-------|--------|-------------|
| PR-1 | **Done** | JSON Schemas, ontology models, Neo4j constraints + upserts, drift checks |
| PR-2 | **Done** | `DeclarationDecomposer`, declaration/checkability/claim-family classification |
| PR-3 | **Done** | `PositionTerm` nodes from `KNS_PersonToPosition`, date-aware office resolution |
| PR-4 | **Done** | Election ingestion, party/list continuity |
| PR-5 | **Done** | Declaration verification, attribution judgments, reviewer/API support |
| PR-6 | Pending | Government decision ingestion |

---

## Completed milestones summary

| Phase | Completed (approx.) | What shipped |
|-------|---------------------|--------------|
| **-1 / 0** | 2026-04-21 | Repo hygiene, compose stack (Postgres, Neo4j, OpenSearch, MinIO), API `/healthz` `/readyz`, migrator, smoke + alignment seed |
| **1** | 2026-04-21 | Postgres pipeline schema, Neo4j constraints + upserts, OpenSearch templates, JSON Schemas + Pydantic ontology, `civic_clients` + archive conventions, integration persistence test |
| **Phase 2** | 2026-04-23 | **Ingestion:** archival service, manifests, jobs queue, entity resolution MVP, five Knesset adapters; **real-data-only** fixtures, CSV votes path, Phase-1 fixture regeneration |
| **2.x** | 2026-04-23 | Historical MK coverage (People cassette); **2.5** join adapters (`positions`, `bill_initiators`, `committee_memberships`, attendance CSV + `MkIndividualLookup`) |
| **3** | 2026-04-23 | Slot templates, rules-first decomposition + prompts, temporal + checkability, entity resolution v2, `ATTENDED` rel, statements tables + gold set recording |
| **4** | 2026-04-23 | Graph + lexical retrieval, reranker, verdict engine + provenance bundle, `/claims/verify` pipeline, review repository + API |
| **Live + 5–6** | 2026-04-26 | Full compose validation (Phase 1–2 integration), gold-set expansion, **`CIVIC_LIVE_WIRING`** API path, reviewer UI + HTMX proxy, eval / regression / freshness, drift-fix wave (protocol, compose, semantic gold, `index_evidence`, `eval` gates) |
| **ER fix wave** | 2026-04-27 | Entity resolution fix wave: regex end-anchors, language-aware resolution, CONTAINS fallback, fuzzy `partial_ratio`, gold-set offline/live split. Offline f1_verdict **0.2 → 1.0** |
| **Live eval green** | 2026-05-01 | Live eval confirmed **f1_verdict = 1.0** (all 10 verdict-pinned rows match). Added `english_name` property to all Neo4j entity upserts (Bill, Office, Committee, Person, Party) to suppress driver warnings. |
| **Auth + logging** | 2026-05-02 | HTTP Basic Auth on reviewer UI (`REVIEWER_UI_PASSWORD` env var, `/healthz` exempt). `civic_common.logging.configure_logging()` shared across API, worker, reviewer UI — JSON in prod, console in dev. Worker + reviewer_ui healthchecks added to docker-compose. |

**Detail:** every wave, file touch, and verification log → [`CHANGELOG.md`](CHANGELOG.md).

---

## Performance baselines

**Offline `make eval`** (default `VerifyPipeline()`, 20-row NL gold set, 2026-04-27):

| Metric | Value |
|--------|--------|
| `rows` | 20 |
| `mean_claim_typing_precision` / `recall` | 1.0 / 1.0 |
| `f1_claim_typing` / `f1_verdict` | **1.0 / 1.0** |

**Live `make eval --live`** (live Neo4j + OpenSearch + `LiveEntityResolver`, 2026-05-02, full Knesset graph):

| Metric | Value |
|--------|--------|
| `rows` | 20 |
| `mean_claim_typing_precision` / `recall` | 1.0 / 1.0 |
| `f1_claim_typing` / `f1_verdict` | **1.0 / 1.0** |

**Entity resolution fixes applied (2026-04-27) — verified live 2026-05-01:**
- **Regex end-anchors:** Added `\s*\Z` to all 10 decomposition patterns in `rules.py` — fixes the "2-char capture" bug where lazy quantifiers stopped too early.
- **Language-aware resolution:** `LiveEntityResolver._is_hebrew()` detection routes Hebrew values to `hebrew_name` and English values to `english_name` in the resolver ladder.
- **CONTAINS fallback:** `_fallback_resolve()` expanded from bill/office-only to all entity kinds, matching across multiple name fields (title, hebrew_name, canonical_name, english_name).
- **Fuzzy scoring:** `_lookup_fuzzy` now considers `canonical_name` + `english_name` + `fuzz.partial_ratio` for substring matches.
- **Gold set dual expectations:** `expected_verdict` = offline baseline; `expected_verdict_live` = live-mode expectation (eval script picks the right one via `--live`).
- **`english_name` property on all labels:** Added to Bill, Office, Committee upserts (Person/Party already had it). Uses `coalesce($english_name, '')` to guarantee property existence and suppress Neo4j driver `01N52` warnings.

**Gates** in `tests/benchmark/config.yaml`: `min_rows: 25`, `f1_verdict: 1.0`, `f1_claim_typing: 1.0`, `abstention_correctness: 1.0`. Both offline and live gate sections present.

---

## Data assets and reports

| Asset | Location |
|-------|----------|
| Eval last run (offline) | [`reports/eval/last_run.json`](../reports/eval/last_run.json) |
| Eval last run (live) | [`reports/eval/last_run_live.json`](../reports/eval/last_run_live.json) |
| Freshness check output | [`reports/freshness_check.json`](../reports/freshness_check.json) |

Standalone HTML reports (per [`.cursor/rules/report-on-completion.mdc`](../.cursor/rules/report-on-completion.mdc)) go under `reports/<name>/` + zip; register new reports here when added.

## Live graph state (post-ingest, 2026-05-02)

Full ingestion run completed via `make ingest` (all 8 adapters, live upstream sources). Duration: 5,566s (~92 min).

**Node counts:**

| Label | Count |
|-------|-------|
| Person | 1,310 |
| Party | 542 |
| Office | 1,205 |
| Committee | 899 |
| Bill | 52,233 |
| VoteEvent | 25,911 |
| AttendanceEvent | 106,331 |
| **Total** | **188,431** |

**Relationship counts:**

| Type | Count |
|------|-------|
| CAST_VOTE | 1,271,812 |
| ATTENDED | 261,054 |
| SPONSORED | 148,144 |
| MEMBER_OF_COMMITTEE | 10,932 |
| MEMBER_OF | 4,464 |
| HELD_OFFICE | 4,295 |
| **Total** | **1,700,701** |

**Per-adapter row counts (single run):**

| Adapter | Source | Pages | Rows upserted | Time |
|---------|--------|-------|---------------|------|
| people | KNS_Person (all) | 12 | 1,184 | 17s |
| positions | KNS_PersonToPosition (all) | 111 | 11,090 | 73s |
| committees | KNS_Committee (K25) | 1 | 89 | 1s |
| committee_memberships | oknesset CSV | 1 | 12,538 | 31s |
| sponsorships | KNS_Bill (K25) | 73 | 7,296 | 45s |
| bill_initiators | KNS_BillInitiator (all) | 1,696 | 148,144 | 797s |
| votes | oknesset CSV | 1 | 1,275,825 | 3,840s |
| attendance | oknesset CSV | 1 | 106,342 | 761s |

---

## Agent scratchpad

_Use this section for **short**, session-specific notes (commands run, branch, blocker). Promote anything durable into [`AGENT_GUIDE.md`](AGENT_GUIDE.md) and trim here._

- **2026-05-03 (session 10 — V2 PR-5):** **V2 PR-5 delivered (Declaration verification + attribution judgments + API/reviewer support).** Added 3 new modules to `services/verification/`: `relation_rules.py` (verdict-to-RelationType mapping with refinement rules for time_scope_mismatch, entity_ambiguous, underspecifies; confidence band bucketing; worst-relation priority), `attribution_judge.py` (builds `AttributionEdge` from v1 verdict + provenance; maps claim_type→ToObjectType, extracts graph entity IDs, collects evidence spans), `declaration_verifier.py` (`DeclarationVerifier` class: Stage A = v1 pipeline re-run, Stage B = relation judgment + edge construction; auto-opens `kind="declaration"` review tasks for ambiguous/contradicted results). Added `"declaration"` to review queue valid kinds. Created `apps/api/src/api/routers/declarations.py` with 3 endpoints: `POST /declarations/ingest`, `POST /declarations/{id}/verify`, `GET /declarations/{id}`. Wired declarations router in `main.py`. Added declaration-focused reviewer UI: `declaration_detail.html` template (quote/source/claims/records/judgment/controls layout), `GET /declarations` route, kind-filter navigation. Added 50 new tests (38 unit + 7 API integration + 5 alignment). Full workspace: **652 passed, 0 failed**. Schema drift check: OK. **Next: V2 PR-6 (government decision ingestion).**
- **2026-05-03 (session 9 — V2 PR-4 gaps):** **PR-4 gap fill:** Knesset 24 CEC cassette (`sample_k24.html` + `SOURCE_K24.md`) + `knesset_24` party/faction mapping in YAML. New `election_result` `ClaimType` with slots `party_id`, `expected_seats`, `expect_passed_threshold` (schema + Pydantic + OpenSearch `claim_cache` template). Hebrew/English decomposition rules; `election_result.cypher` retrieval; verdict engine seat/threshold checks; pipeline party resolution + time_scope → graph params; `electoral_claim` family. Phase-1 persistence test refreshes OS templates before `claim_cache` index. **602 passed, 0 failed**. **Next: V2 PR-5.**
- **2026-05-03 (session 8 — V2 PR-4):** **V2 PR-4 delivered (Election ingestion + party/list continuity).** Extended `ElectionResult` schema/model/upsert with `knesset_number`, `list_name`, `ballot_letters`. Recorded official CEC Knesset 25 national results page (`votes25.bechirot.gov.il`) as a Tier-1 cassette (40 lists, 4,764,742 valid votes). Built `civic-ingest-elections` adapter package: `parse.py` (regex HTML parser handles broken-attribute rows like Shas), `normalize.py` (threshold = `ceil(valid_votes × 0.0325)`, deterministic UUIDs), `upsert.py` (Party stub + ElectionResult + FOR_PARTY), `party_list_mapping.yaml` (K25 ballot_letters → KNS FactionID for all 10 threshold-passing lists). Added `election_results` to `AdapterKind` in manifest.py + source_manifest.schema.json. Registered adapter in `scripts/ingest_all.sh` and root `pyproject.toml`. Added 20 unit tests (all pass). Full workspace: **583 passed, 0 failed**. Schema drift check: OK. **Next: V2 PR-5 (declaration verification, attribution judgments, reviewer/API support).**
- **2026-05-03 (session 7 — V2 PR-3):** **V2 PR-3 delivered (PositionTerm nodes + date-aware office resolution).** Promoted `KNS_PersonToPosition` ministerial position data to first-class `PositionTerm` nodes. Added `NormalizedPositionTerm` dataclass to the positions normalizer (keyed `uuid5(…, "knesset_position_term:{PersonToPositionID}")`; `appointing_body` = `"government"` for PM/minister/deputy, `"knesset"` for MK/committee roles). Extended positions upsert to emit 3 additional Neo4j writes per office row: `PositionTerm` node + `HAS_POSITION_TERM` + `ABOUT_OFFICE` edges (legacy `HELD_OFFICE` preserved for backward compat). Updated `infra/neo4j/retrieval/office_held.cypher` to use V2 PositionTerm path with UNION fallback to legacy `HELD_OFFICE`. Added `position_term_resolver.py` to `services/entity_resolution/` with `resolve_position_terms()` for date-bounded office holding lookups. Added 20 new tests (15 adapter + 10 resolver + 3 alignment). Full workspace: **560 passed, 0 failed**. **Next: V2 PR-4 (election ingestion, party/list continuity).**
- **2026-05-02 (session 6 — V2 PR-2):** **V2 PR-2 delivered (DeclarationDecomposer layer).** Added 4 new modules to `services/claim_decomposition/`: `claim_family_classifier.py` (maps `ClaimType` → `ClaimFamily`), `declaration_checkability.py` (aggregates per-claim checkability → `DeclarationCheckability`), `temporal_scope_extractor.py` (wraps `civic_temporal.normalize_time_scope` + year/ISO-date extraction from utterance text), and `declaration_decomposer.py` (`DeclarationDecomposer` class — wraps v1 `decompose()`, always emits a `Declaration` + derived `DecomposedClaim` list). Updated `__init__.py` exports. Added 38 new unit tests (all pass). Full workspace: **540 passed, 0 failed**. `VerifyPipeline` and `/claims/verify` are untouched. **Next: V2 PR-3 (gov.il role ingestion, PositionTerm, date-aware office resolution).**
- **2026-05-02 (session 5 — V2 PR-1):** **V2 PR-1 delivered (schema layer).** Added 5 new JSON Schemas (`declaration`, `attribution_edge`, `position_term`, `government_decision`, `election_result`) under `data_contracts/jsonschemas/`. Added matching Pydantic ontology models under `packages/ontology/src/civic_ontology/models/`. Updated `MODEL_TO_SCHEMA` in `schemas.py` (17 entries total); drift check exits 0. Added 4 new Neo4j uniqueness constraints (`Declaration`, `PositionTerm`, `GovernmentDecision`, `ElectionResult`) to `infra/neo4j/constraints.cypher`. Created 4 node upsert templates + 8 relationship templates (`said_by`, `from_source`, `derives`, `refers_to`, `has_position_term`, `about_office`, `concerns`, `for_party`). Extended `tests/smoke/test_alignment.py` with V2 node/schema/relationship assertions; updated node upsert count (12→16) and relationship count (13→21). Added 5 enum-pinning drift tests to `packages/ontology/tests/test_schema_drift.py`. Updated `docs/DATA_MODEL.md` with V2 graph section. **Next: V2 PR-2 (DeclarationDecomposer).**
- **2026-05-02 (session 4 — v1 close-out):** **All remaining v1 work items completed.** (1) Gold set expanded from 20 → 26 rows; (2) GitHub Actions CI/CD created (lint + test + offline eval); (3) `docs/DEPLOYMENT.md` written; (4) Doc drift fixed (ARCHITECTURE, cassette-recording, source-manifests, DATA_MODEL); (5) `eval.py` expanded with provenance_completeness + abstention_correctness + live gates in config.yaml; (6) `seed-demo.sh` now replays all 8 cassettes via `scripts/seed_demo.py`; (7) Stub service READMEs updated to v2, empty test dirs replaced with convention READMEs; (8) `vote_event_about_bill.cypher` + `scripts/enrich_vote_bills.py` + `make enrich-vote-bills` for ABOUT_BILL enrichment. 471 tests pass. **v1 is fully shipped.**
- **2026-05-02 (session 3):** **Full Knesset data ingestion.** Created `scripts/ingest_all.sh` (prerequisite checks, 8 adapters in dependency order, timing, `--dry-run`/`--max-pages`/`--skip-index` flags) + `make ingest` / `make ingest-dry` targets. Fixed a latent bug in `services/ingestion/_common/src/civic_ingest/adapter.py`: Knesset OData V3 returns relative `odata.nextLink` URLs (e.g. `KNS_Person?$skip=100&…`); added `urllib.parse.urljoin` resolution so multi-page crawls work. Full crawl result: **188,431 nodes**, **1,700,701 relationships** loaded into Neo4j; total runtime 5,566s. Re-pinned `nl_he_committee_membership` live verdict (`insufficient_evidence` → `non_checkable`): full graph has 899 committees so CONTAINS fallback is now ambiguous. Live eval confirmed **f1_verdict = 1.0** (all 20 rows). 470 tests pass.
- **2026-05-02 (session 2):** **Reviewer UI auth + structured logging.** Added HTTP Basic Auth to all reviewer UI routes (shared `REVIEWER_UI_PASSWORD` env var, timing-safe `secrets.compare_digest`, `/healthz` exempt). Created `civic_common.logging.configure_logging()` — JSON renderer in non-dev, console in dev, bridges stdlib root logger. Wired into API, worker, and reviewer UI. Worker file-touch sentinel + reviewer UI `/healthz` probe added to docker-compose healthchecks. 470 passed, 0 skipped; 197/197 alignment rows.
- **2026-05-02 (session 1):** **Eliminated all 5 test skips.** Root causes: (1) `NEO4J_PASSWORD` mismatch between `.env` (`Polazin2!`) and test conftest defaults (`civic_dev_pw`) — fixed by new workspace-root `conftest.py` that auto-loads `.env` via `python-dotenv` and remaps container DNS → localhost. (2) `python-multipart` not installed in root venv (reviewer_ui dep) — fixed by adding to root dev group + `uv sync --all-packages`. (3) `_office_params` missing `hebrew_name`/`english_name` keys after recent cypher updates — fixed. 461 passed, 0 skipped, 0 failed.
- **2026-05-01:** **Live eval confirmed f1_verdict = 1.0.** Ran `uv run python scripts/eval.py --live` (requires `source .env` + localhost overrides via bash). Added `english_name` property to Bill/Office/Committee/Person/Party Cypher upserts with `coalesce(..., '')` default — eliminates Neo4j `01N52` driver warnings. Updated adapter callers to pass the new param.
- **2026-04-27:** **Entity Resolution Fix Wave.** Four compounding bugs fixed: (1) regex lazy quantifiers without end-anchors, (2) language-blind entity resolution, (3) no CONTAINS fallback for partial names, (4) fuzzy scoring too narrow. Plus gold-set modelling gap (offline vs live expectations). Offline f1_verdict **0.2 → 1.0**. All 438+190 tests pass. Pitfalls promoted to `AGENT_GUIDE.md`. Full detail → [`CHANGELOG.md`](CHANGELOG.md).
- **2026-04-27:** Doc split (STATUS/CHANGELOG/AGENT_GUIDE) + graph brought alive (505 nodes, 747 rels). See [`CHANGELOG.md`](CHANGELOG.md).

---

## Related docs

| Doc | Role |
|-----|------|
| [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | Pitfalls, invariants, ADR/convention index |
| [`CHANGELOG.md`](CHANGELOG.md) | Milestone-by-milestone implementation history |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture |
| [`DATA_MODEL.md`](DATA_MODEL.md) | ERD / graph / index overview |
| [`political_verifier_v_1_plan.md`](political_verifier_v_1_plan.md) | v1 product + phase spec |
