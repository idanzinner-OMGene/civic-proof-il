# Project Status — civic-proof-il Political Verifier

> **Single source of truth** for current state, priorities, and baselines. **Implementation history** → [`CHANGELOG.md`](CHANGELOG.md). **Decisions, pitfalls, invariants** → [`AGENT_GUIDE.md`](AGENT_GUIDE.md).  
> Agents: read this file **before and after** substantive work; append short session notes to [Agent scratchpad](#agent-scratchpad).

---

## Current state (read this first)

- **Product:** Knowledge-graph-backed verifier for Israeli national political statements — decompose → resolve → retrieve (Neo4j + OpenSearch) → deterministic verdict + review queue. Spec: [`political_verifier_v_1_plan.md`](political_verifier_v_1_plan.md).
- **Phases 0–6 (v1 scaffold):** Delivered — monorepo, canonical model, Knesset ingestion (8 adapters + real-data cassettes), join adapters (2.5), claim pipeline, retrieval + verdict API, reviewer UI, eval / regression / freshness harness. See [Completed milestones](#completed-milestones-summary) and [`CHANGELOG.md`](CHANGELOG.md).
- **Stack:** `make up` — Postgres 16, Neo4j 5 Community, OpenSearch 2, MinIO, migrator, API, worker, reviewer UI (port 8001). Host-side integration tests need explicit env overrides to `localhost` (see [`AGENT_GUIDE.md`](AGENT_GUIDE.md)).
- **Tests:** Workspace run (no Docker smoke): **470 passed, 0 skipped** (last run, 2026-05-02). **197/197** alignment smoke rows; **5/5** regression. **`make eval`** exits 0 with current gates.
- **Live wiring in tests:** For API integration against real backends, set **`CIVIC_LIVE_WIRING=1`** with `ENV=test` or `ci` so lifespan mounts graph + lexical retrievers (see [`AGENT_GUIDE.md`](AGENT_GUIDE.md)).

---

## Next priorities

| # | Track | Description | Priority |
|---|--------|-------------|----------|
| 1 | Product | ~~Reviewer UI auth~~ ✓ done; deployment monitoring for Phase 6 | Medium |
| 2 | Data | Populate `bill_id` → ABOUT_BILL link (votes CSV lacks BillID); enables vote_cast live verification | Low |
| 3 | Quality | Add real-entity gold-set rows (Hebrew names in graph) with `supported`/`contradicted` verdicts | Low |

Acceptance criteria and ticket-level scope: [`political_verifier_v_1_plan.md`](political_verifier_v_1_plan.md).

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

**Live `make eval --live`** (live Neo4j + OpenSearch + `LiveEntityResolver`, 2026-05-01):

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

**Gates** in `tests/benchmark/config.yaml` (OFFLINE only, no live retrieval): `min_rows: 10`, `f1_verdict: 1.0`, `f1_claim_typing: 1.0`.

---

## Data assets and reports

| Asset | Location |
|-------|----------|
| Eval last run (offline) | [`reports/eval/last_run.json`](../reports/eval/last_run.json) |
| Eval last run (live) | [`reports/eval/last_run_live.json`](../reports/eval/last_run_live.json) |
| Freshness check output | [`reports/freshness_check.json`](../reports/freshness_check.json) |

Standalone HTML reports (per [`.cursor/rules/report-on-completion.mdc`](../.cursor/rules/report-on-completion.mdc)) go under `reports/<name>/` + zip; register new reports here when added.

---

## Agent scratchpad

_Use this section for **short**, session-specific notes (commands run, branch, blocker). Promote anything durable into [`AGENT_GUIDE.md`](AGENT_GUIDE.md) and trim here._

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
