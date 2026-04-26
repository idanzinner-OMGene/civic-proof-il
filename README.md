# civic-proof-il — Political Verifier

A knowledge-graph-backed verifier for Israeli national political statements. Given a single statement, the system decomposes it into atomic claims, retrieves official evidence from Tier 1 sources (Knesset records, gov.il), and returns a conservative verdict with full archived provenance.

**In scope for v1:** MKs, ministers, deputy ministers, and canonical party leaders. Claim types: vote cast, bill sponsorship, office held, committee membership, committee attendance, and formal-action statements reducible to one of these.

## Documentation

- [Project plan — Political Verifier v1](docs/political_verifier_v_1_plan.md)
- [Project status](docs/PROJECT_STATUS.md) · [Agent guide](docs/AGENT_GUIDE.md) · [Changelog](docs/CHANGELOG.md)

## Getting started

1. `cp .env.example .env` and adjust secrets (Neo4j volume / password gotchas: `docs/AGENT_GUIDE.md`).
2. `uv sync --all-packages --group dev`
3. `make up` — brings up Postgres, Neo4j, OpenSearch, MinIO, migrator, **api** (8000), **worker**, **reviewer_ui** (8001).
4. `uv run pytest` — full unit + alignment; live smoke and integration that touch Docker are skipped or require the stack and env overrides (`docs/PROJECT_STATUS.md`, pitfalls in `docs/AGENT_GUIDE.md`).

**Gold-set recording:** `uv run python scripts/record-statements.py tests/fixtures/phase3/manifests/gold_set.jsonl --insecure-ssl` (only if you hit TLS trust issues to `knesset.gov.il`).

**Eval / freshness (Phase 6):** `make eval` · `make freshness` (write under `reports/`, git-ignored JSON paths).

## Architecture

Services: `apps/api` (FastAPI verify + review API), `apps/worker` (ingestion jobs), `apps/reviewer_ui` (read-only queue browser calling the main API), packages under `packages/` and `services/`. Infrastructure: Neo4j, OpenSearch, PostgreSQL, MinIO via `infra/docker/docker-compose.yml`.

See [docs/political_verifier_v_1_plan.md](docs/political_verifier_v_1_plan.md) for the full spec, data model, and eight-week schedule.
