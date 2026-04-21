# Contributing to civic-proof-il

Authoritative references:

- Spec: [`docs/political_verifier_v_1_plan.md`](docs/political_verifier_v_1_plan.md)
- Live status: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- Architecture overview: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Local setup

1. Install [uv](https://docs.astral.sh/uv/) (Python package and workspace manager).
2. Sync the workspace:
   ```bash
   bash scripts/bootstrap-dev.sh
   ```
3. Copy the env file and edit if needed:
   ```bash
   cp .env.example .env
   ```

## Day-to-day

- `make up` — start the docker-compose stack (Postgres, Neo4j, OpenSearch, MinIO, API, worker).
- `make test` — run the full test suite.
- `make down` — stop the stack.

## House rules

1. Update `docs/PROJECT_STATUS.md` at the end of every agent session or milestone — it is the single source of truth for cross-agent context.
2. Never commit `.env` or any real secret. Use `.env.example` for documented defaults only.
3. Deterministic code before LLM calls. LLMs assist decomposition, temporal normalization, and summarization; they must not decide canonical truth.
4. All Tier-1 sources must be archived (content-hashed, immutable URI) before they can back a verdict.
