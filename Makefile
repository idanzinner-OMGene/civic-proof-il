SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

COMPOSE_FILE := infra/docker/docker-compose.yml
ENV_FILE := .env
COMPOSE := docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE)

.PHONY: help bootstrap up down restart logs ps test smoke seed-demo migrate fmt lint clean record-cassettes eval eval-live freshness ingest ingest-dry enrich-vote-bills

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap:  ## Copy .env.example to .env if missing, then uv sync
	bash scripts/bootstrap-dev.sh

up:  ## Start the full stack (compose up -d --build --wait)
	$(COMPOSE) up -d --build --wait

down:  ## Stop the stack and remove volumes
	$(COMPOSE) down -v

restart:  ## Restart the stack
	$(MAKE) down
	$(MAKE) up

logs:  ## Tail all service logs
	$(COMPOSE) logs -f

ps:  ## Show service status
	$(COMPOSE) ps

migrate:  ## Run database migrations
	bash scripts/run-migrations.sh

test:  ## Run unit tests (workspace-wide, no stack needed)
	uv run pytest apps/api/tests apps/worker/tests -v

smoke:  ## Run smoke/integration tests (requires `make up` first)
	uv run pytest tests/smoke -v

seed-demo:  ## Seed demo data (Phase 0: calls /readyz)
	bash scripts/seed-demo.sh

fmt:  ## Format code with ruff
	uv run ruff format .

lint:  ## Lint code with ruff
	uv run ruff check .

clean:  ## Stop stack + remove local venvs
	-$(MAKE) down
	rm -rf .venv apps/*/.venv packages/*/.venv

record-cassettes:  ## Re-record every Phase-2 test cassette from the live upstream
	bash scripts/record-cassettes.sh

eval:  ## Run Phase-6 benchmark harness (offline; writes reports/eval/last_run.json)
	uv run python scripts/eval.py

eval-live:  ## Run Phase-6 benchmark against the live stack (requires `make up`; writes reports/eval/last_run_live.json)
	bash -c 'set -a; source .env; set +a; export POSTGRES_HOST=localhost NEO4J_URI=bolt://localhost:7687 OPENSEARCH_URL=http://localhost:9200 MINIO_ENDPOINT=localhost:9000; uv run python scripts/eval.py --live'

freshness:  ## Emit ingest manifest freshness report (JSON under reports/)
	uv run python scripts/freshness_check.py

index-evidence:  ## Index evidence_spans in OpenSearch from Neo4j SourceDocument nodes
	uv run python scripts/index_evidence.py

ingest:  ## Run full Knesset ingestion pipeline — all 8 adapters + evidence index (requires `make up`)
	bash scripts/ingest_all.sh

ingest-dry:  ## Dry-run ingestion — fetch + parse only, no Neo4j writes (requires `make up` for Postgres)
	bash scripts/ingest_all.sh --dry-run

enrich-vote-bills:  ## Enrich VoteEvent nodes with bill_id + ABOUT_BILL edges from KNS_Vote OData (requires `make ingest` first)
	bash -c 'set -a; source .env; set +a; export POSTGRES_HOST=localhost NEO4J_URI=bolt://localhost:7687; uv run python scripts/enrich_vote_bills.py'
