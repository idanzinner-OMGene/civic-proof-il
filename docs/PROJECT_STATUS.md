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

---

## In progress

_(nothing currently in progress — Phase 0 complete, Phase 1 not yet started)_

---

## Remaining pipeline — priority order

| # | Phase | Description | Priority |
|---|-------|-------------|----------|
| 1 | Canonical data model | PostgreSQL schema, Neo4j constraints + upsert conventions, OpenSearch index mappings, JSON schemas | high |
| 2 | Ingestion — first family | People/roles, committees/memberships, vote results, bill sponsorship, attendance adapters | high |
| 3 | Atomic claim pipeline | Statement intake API, rule-first decomposition, ontology mapper, entity resolution, temporal normalizer, checkability classifier | high |
| 4 | Retrieval + verification | Graph retrieval, lexical+vector retrieval, deterministic reranker, verdict engine, abstention policy, provenance bundle | high |
| 5 | Review workflow | Reviewer queue, conflict queue, entity-resolution correction, verdict override with audit log | medium |
| 6 | Hardening + evaluation | Benchmark set, offline eval harness, regression tests, provenance completeness tests, freshness monitoring | medium |

Acceptance criteria and detailed deliverables for each phase are in [political_verifier_v_1_plan.md](political_verifier_v_1_plan.md).

> Phase 0 moved to Completed milestones on 2026-04-21.

---

## Cross-step knowledge

> Future agents: append persistent context here — gotchas, data quirks, design decisions, performance baselines, known limitations — so it survives across sessions.

### Design decisions
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

### Known gotchas
- **Migrator Dockerfile pulls `cypher-shell_5.23.0_all.deb` from `dist.neo4j.org` at build time.** If Neo4j version is bumped or the URL changes, update `apps/migrator/Dockerfile`. cypher-shell is the Neo4j 5 client; major-version skew between client and server is usually fine but keep them in sync when possible.
- **Alembic URL is constructed in `env.py`**, not `alembic.ini`. `sqlalchemy.url` in `alembic.ini` is intentionally blank so the env-var contract is the single source of truth. Do not hardcode credentials there.
- **`scripts/run-migrations.sh` is dual-mode.** Inside the migrator container it uses `ROOT_DIR=/app`; on the host it resolves `ROOT_DIR` from its own location (`$(dirname "$0")/..`). Keep this behavior when extending.
- **`schema_migrations_info` table is a phase-0 bookkeeping placeholder.** Real domain schema starts in Phase 1; do not build on this table.
- **macOS Docker Desktop must be running** for `make up` — the stack cannot start if the Docker daemon is not up. Wave-2 audit deferred the full `make up` smoke run for this reason on the author's machine.
- **`uv` must be on PATH** for `make test` / `make smoke` — Wave-2 audit could not exercise `uv run pytest` locally because `uv` was not installed; use `scripts/bootstrap-dev.sh` (or `curl -LsSf https://astral.sh/uv/install.sh | sh`) first.
- **Scripts were committed with the `+x` bit set** (verified via `git ls-files --stage scripts/`). Fresh clones get executable scripts automatically; the `Makefile` also falls back to `bash scripts/<name>.sh` so either path works.
- **API tests import `api.main` at module load**, and `api.main` calls `create_app()` → `get_settings()` at module level. Per-test `monkeypatch` fixtures run too late — `apps/api/tests/conftest.py` also sets the required env vars with `os.environ.setdefault(...)` at conftest-load time. Do NOT remove that block without moving `app = create_app()` out of module scope first.
- **OpenSearch 2.12+ enforces strong admin passwords (min 8 chars, upper/lower/digit/special)** when the security plugin is enabled. Our compose sets `DISABLE_SECURITY_PLUGIN=true`, so `admin/admin` works. If anyone re-enables the security plugin, the password in `.env.example` must be upgraded (e.g. `Civic_Dev_Pw!2026`).
- **`tests/smoke/conftest.py` honors `*_HOST` env-var variants** (e.g. `POSTGRES_HOST_HOST`, `NEO4J_URI_HOST`, `OPENSEARCH_URL_HOST`, `MINIO_ENDPOINT_HOST`). This lets tests on the host machine hit the docker-compose published ports (`localhost:5432`, etc.) while the container-local `.env` still uses in-network hostnames (`postgres:5432`). Keep both when adding new backing stores.

### Performance baselines
_(append after first eval run)_
