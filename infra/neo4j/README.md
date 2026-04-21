# Neo4j — config and placeholder init

Neo4j config + placeholder init script. Real constraints live in
`infra/neo4j/constraints.cypher` (populated by the migrator in Phase 0+).
This `init.cypher` is a smoke-test script devs can run to sanity-check
`cypher-shell` connectivity against the running container.

## Smoke test

```bash
docker compose -f infra/docker/docker-compose.yml exec -T neo4j \
  cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < infra/neo4j/init.cypher
```

Expect a single row: `ok = 1`.
