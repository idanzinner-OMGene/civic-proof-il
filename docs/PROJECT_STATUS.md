# Project Status — civic-proof-il Political Verifier

> **Single source of truth** for current state, priorities, and baselines. **Implementation history** → [`CHANGELOG.md`](CHANGELOG.md). **Decisions, pitfalls, invariants** → [`AGENT_GUIDE.md`](AGENT_GUIDE.md).  
> Agents: read this file **before and after** substantive work; append short session notes to [Agent scratchpad](#agent-scratchpad).

---

## Current state (read this first)

- **Product:** Knowledge-graph-backed verifier for Israeli national political statements — decompose → resolve → retrieve (Neo4j + OpenSearch) → deterministic verdict + review queue. Spec: [`political_verifier_v_1_plan.md`](political_verifier_v_1_plan.md).
- **Phases 0–6 (v1 scaffold):** Delivered — monorepo, canonical model, Knesset ingestion (8 adapters + real-data cassettes), join adapters (2.5), claim pipeline, retrieval + verdict API, reviewer UI, eval / regression / freshness harness. See [Completed milestones](#completed-milestones-summary) and [`CHANGELOG.md`](CHANGELOG.md).
- **Stack:** `make up` — Postgres 16, Neo4j 5 Community, OpenSearch 2, MinIO, migrator, API, worker, reviewer UI (port 8001). Host-side integration tests need explicit env overrides to `localhost` (see [`AGENT_GUIDE.md`](AGENT_GUIDE.md)).
- **Tests:** Workspace run (no Docker smoke): **434 passed, 4 skipped** (last logged run, 2026-04-26). **190/190** alignment smoke rows; **5/5** regression (1 Neo4j integration skipped when unreachable). **`make eval`** exits 0 with current gates.
- **Live wiring in tests:** For API integration against real backends, set **`CIVIC_LIVE_WIRING=1`** with `ENV=test` or `ci` so lifespan mounts graph + lexical retrievers (see [`AGENT_GUIDE.md`](AGENT_GUIDE.md)).

---

## Next priorities

| # | Track | Description | Priority |
|---|--------|-------------|----------|
| 1 | v1 follow-up | Pin non-empty `expected.expected_claim_types` / `expected_verdict` on semantic gold rows; add stable natural-language transcript sources when fetch paths exist | **High** |
| 2 | Phase 6+ | Tighten [`tests/benchmark/config.yaml`](../tests/benchmark/config.yaml) gates using measured `make eval` baselines on a **loaded** stack | Medium |
| 3 | Product | Reviewer UI auth; deployment monitoring for Phase 6 | Low |

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

**Detail:** every wave, file touch, and verification log → [`CHANGELOG.md`](CHANGELOG.md).

---

## Performance baselines

**Offline `make eval`** (default `VerifyPipeline()`, semantic gold expansion, 2026-04-26):

| Metric | Value |
|--------|--------|
| `rows` | 10 |
| `mean_claim_typing_precision` / `recall` | 0.0 / 0.0 |
| `f1_claim_typing` / `f1_verdict` | 0.0 / 0.0 |

Gold inputs are real recorded OData (structured JSON); F1 stays **0.0** until live graph + lexical retrieval and richer NL statements drive non-abstaining paths. **Gates** in `tests/benchmark/config.yaml`: `min_rows: 4`, `f1_verdict: 0.0`, `f1_claim_typing: 0.0` — tighten after measured baselines on a loaded stack.

---

## Data assets and reports

| Asset | Location |
|-------|----------|
| Eval last run | [`reports/eval/last_run.json`](../reports/eval/last_run.json) |
| Freshness check output | [`reports/freshness_check.json`](../reports/freshness_check.json) |

Standalone HTML reports (per [`.cursor/rules/report-on-completion.mdc`](../.cursor/rules/report-on-completion.mdc)) go under `reports/<name>/` + zip; register new reports here when added.

---

## Agent scratchpad

_Use this section for **short**, session-specific notes (commands run, branch, blocker). Promote anything durable into [`AGENT_GUIDE.md`](AGENT_GUIDE.md) and trim here._

- **2026-04-27:** Split monolithic status doc into [`CHANGELOG.md`](CHANGELOG.md) (milestone history), [`AGENT_GUIDE.md`](AGENT_GUIDE.md) (pitfalls + decisions by topic), and this file (current state + priorities). README / CONTRIBUTING / ARCHITECTURE / service READMEs updated for links. Alignment `test_alignment.py`: **190 passed**.

---

## Related docs

| Doc | Role |
|-----|------|
| [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | Pitfalls, invariants, ADR/convention index |
| [`CHANGELOG.md`](CHANGELOG.md) | Milestone-by-milestone implementation history |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture |
| [`DATA_MODEL.md`](DATA_MODEL.md) | ERD / graph / index overview |
| [`political_verifier_v_1_plan.md`](political_verifier_v_1_plan.md) | v1 product + phase spec |
