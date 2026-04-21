FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl wget ca-certificates bash procps \
    && rm -rf /var/lib/apt/lists/*

# Install cypher-shell (Neo4j 5)
RUN curl -fsSL https://dist.neo4j.org/cypher-shell/cypher-shell_5.23.0_all.deb -o /tmp/cs.deb \
    && apt-get update && apt-get install -y --no-install-recommends /tmp/cs.deb openjdk-17-jre-headless \
    && rm -f /tmp/cs.deb && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY apps/migrator/pyproject.toml /app/apps/migrator/pyproject.toml
RUN uv pip install --system --no-cache alembic "psycopg[binary]" sqlalchemy

COPY infra/migrations /app/infra/migrations
COPY infra/neo4j/constraints.cypher /app/infra/neo4j/constraints.cypher
COPY infra/opensearch/templates /app/infra/opensearch/templates
COPY scripts/run-migrations.sh /app/scripts/run-migrations.sh
RUN chmod +x /app/scripts/run-migrations.sh

WORKDIR /app
ENTRYPOINT ["/app/scripts/run-migrations.sh"]
