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

---

## In progress

_(nothing currently in progress)_

---

## Remaining pipeline — priority order

| # | Phase | Description | Priority |
|---|-------|-------------|----------|
| 0 | Bootstrap | Monorepo scaffold, docker-compose (Neo4j, OpenSearch, PostgreSQL, MinIO), Makefile, `.env.example`, migrations, smoke tests | **immediate** |
| 1 | Canonical data model | PostgreSQL schema, Neo4j constraints + upsert conventions, OpenSearch index mappings, JSON schemas | high |
| 2 | Ingestion — first family | People/roles, committees/memberships, vote results, bill sponsorship, attendance adapters | high |
| 3 | Atomic claim pipeline | Statement intake API, rule-first decomposition, ontology mapper, entity resolution, temporal normalizer, checkability classifier | high |
| 4 | Retrieval + verification | Graph retrieval, lexical+vector retrieval, deterministic reranker, verdict engine, abstention policy, provenance bundle | high |
| 5 | Review workflow | Reviewer queue, conflict queue, entity-resolution correction, verdict override with audit log | medium |
| 6 | Hardening + evaluation | Benchmark set, offline eval harness, regression tests, provenance completeness tests, freshness monitoring | medium |

Acceptance criteria and detailed deliverables for each phase are in [political_verifier_v_1_plan.md](political_verifier_v_1_plan.md).

---

## Cross-step knowledge

> Future agents: append persistent context here — gotchas, data quirks, design decisions, performance baselines, known limitations — so it survives across sessions.

### Design decisions
- **Conservative abstention by default.** A verdict requires at least one Tier 1 source. Tier 1 conflicts must go to human review. No verdict without archived provenance.
- **LLM role is strictly limited.** LLMs may assist claim decomposition, temporal normalization, evidence summarization, and reviewer explanations. They must NOT make canonical fact promotion, conflict resolution between official records, or direct database writes.
- **Deterministic/rule-first everywhere.** Rules before LLM in decomposition and entity resolution. Deterministic verdict engine in v1; LLMs summarize evidence only.
- **Source tiers are enforced structurally.** Tier 1: official Knesset records, gov.il role pages, government decision records, official election results. Tier 2: contextual official material. Tier 3: discovery-only (media, watchdogs, mirrors).

### Known gotchas
_(append here as discovered)_

### Performance baselines
_(append after first eval run)_
