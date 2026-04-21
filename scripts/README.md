# scripts/

Helper scripts used by the `Makefile` and CI.

| Script | Purpose |
|--------|---------|
| bootstrap-dev.sh | One-time dev setup: ensure `.env`, `uv sync` |
| wait-for-services.sh | Block until all compose services report healthy |
| seed-demo.sh | Phase-0 stub — calls `/readyz` and prints result |
| run-migrations.sh | Apply Postgres / Neo4j / OpenSearch migrations (owned by migrator image) |

After cloning, run once:

    chmod +x scripts/*.sh

Then:

    make bootstrap
    make up
    make migrate
    make smoke
