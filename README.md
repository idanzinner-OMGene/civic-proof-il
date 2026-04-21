# civic-proof-il — Political Verifier

A knowledge-graph-backed verifier for Israeli national political statements. Given a single statement, the system decomposes it into atomic claims, retrieves official evidence from Tier 1 sources (Knesset records, gov.il), and returns a conservative verdict with full archived provenance.

**In scope for v1:** MKs, ministers, deputy ministers, and canonical party leaders. Claim types: vote cast, bill sponsorship, office held, committee membership, committee attendance, and formal-action statements reducible to one of these.

## Documentation

- [Project plan — Political Verifier v1](docs/political_verifier_v_1_plan.md)
- [Project status](docs/PROJECT_STATUS.md)

## Getting started

> Phase 0 bootstrap is not yet complete. This section will be filled when `make up` / `make test` / `make seed-demo` are available.

## Architecture

> High-level architecture diagram and service overview will be added during Phase 0.

Services planned: `apps/api`, `apps/worker`, `apps/reviewer_ui`, plus supporting packages for ontology, entity resolution, claim decomposition, retrieval, verification, and review. Infrastructure: Neo4j, OpenSearch, PostgreSQL, MinIO via docker-compose.

See [docs/political_verifier_v_1_plan.md](docs/political_verifier_v_1_plan.md) for the full spec, data model, and eight-week schedule.
