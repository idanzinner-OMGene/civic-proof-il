# ADR-0001: Canonical data model split across Postgres, Neo4j, OpenSearch, and MinIO

*   **Status:** Accepted
*   **Date:** 2026-04-21
*   **Deciders:** civic-proof-il core team (Phase 1 Wave-1 bootstrap)

## Context and Problem Statement

Phase 1 of `docs/political_verifier_v_1_plan.md` requires a canonical data model that supports three concurrent concerns:

1. A **conservative verdict engine** that only emits supported/contradicted outcomes when at least one Tier 1 source is archived and attached (plan lines 31-65).
2. A **provenance archive** guaranteeing that no verdict exists without an immutable, content-addressed source object.
3. A **human review workflow** that can inspect, relink, and audit any mutation without silently rewriting canonical facts.

Competing design forces: domain facts want expressive graph queries (offices held across time, committee co-membership, vote-to-bill sponsorship chains); ingestion wants a strong operational schema with foreign keys and transactional state; retrieval wants full-text + vector search over Hebrew-language evidence; archival wants write-once content-hashed storage. No single store satisfies all four cleanly, and combining them naively risks tangled write paths, duplicated systems of record, and ambiguous source-of-truth semantics.

We need to decide (a) which store owns which slice of the domain, (b) how entities are identified across stores, and (c) which format and validation dialect governs inter-service contracts.

## Considered Options

1. **Split by concern across Postgres + Neo4j + OpenSearch + MinIO, UUID4 canonical IDs, JSON Schema Draft 2020-12 with Pydantic v2 as source of truth.** The full plan-aligned layout.
2. **Single-store in Postgres** with recursive CTEs / `ltree` / `pg_trgm` / `pgvector` for graph, full-text, and vector concerns, plus bytea or S3 for raw artifacts.
3. **ArangoDB** multi-model (documents + graph + full-text) plus MinIO for archive, collapsing three of the four stores into one.
4. **Elasticsearch** instead of OpenSearch for text/vector retrieval.
5. **INT PKs instead of UUIDs** for cross-store joins, with a central ID issuer service.

## Decision Outcome

Chosen option: **Option 1 — split by concern across Postgres + Neo4j + OpenSearch + MinIO, UUID4 canonical IDs, JSON Schema Draft 2020-12 with Pydantic v2 as single source of truth.**

Concretely:

1. **UUID4 strings as canonical business keys for every entity**, with surrogate `BIGSERIAL` PKs in Postgres for locality-of-reference, FK efficiency, and stable insert ordering. `<entity>_id UUID UNIQUE NOT NULL` columns carry the cross-store identity. Neo4j and OpenSearch use the same UUIDs as node/document keys.
2. **Postgres owns ingest / review / verify pipelines.** It holds operational state — `ingest_runs`, `raw_fetch_objects`, `parse_jobs`, `normalized_records`, `entity_candidates`, `review_tasks`, `review_actions`, `verification_runs`, `verdict_exports`. It does not store domain facts directly. The domain-fact system of record is Neo4j.
3. **Neo4j 5 community holds all domain facts.** `Person`, `Party`, `Office`, `Committee`, `Bill`, `VoteEvent`, `AttendanceEvent`, `MembershipTerm`, `SourceDocument`, `EvidenceSpan`, `AtomicClaim`, `Verdict`, and the eleven relationships defined in the plan. Writes are idempotent via parameterized `MERGE` upsert templates under `infra/neo4j/upserts/`.
4. **OpenSearch is a derived search/cache index**, not a system of record. Three indexes: `source_documents`, `evidence_spans`, `claim_cache`. Any record in OpenSearch has a corresponding canonical write in Neo4j (and/or Postgres for pipeline state). OpenSearch can be rebuilt from scratch by reindexing from Neo4j + MinIO.
5. **MinIO holds raw archive objects keyed by SHA-256** over the raw bytes. Archive objects are immutable. URI convention: `s3://<MINIO_BUCKET_ARCHIVE>/<source_family>/<YYYY>/<MM>/<DD>/<sha256>.<ext>`. No verification-grade verdict may exist without an archived source object (plan line 320).
6. **JSON Schema Draft 2020-12 for all contracts**, under `data_contracts/jsonschemas/`. **Pydantic v2** models in `packages/ontology/` are the single source of truth; JSON Schemas are regenerated from the Pydantic models and drift is enforced by CI.

Write ordering across stores is fixed: **Postgres first** (to record ingest / parse / normalize state), **then Neo4j** (to commit domain facts once normalization has passed), **then OpenSearch** (to refresh the search cache). Rollback semantics are per-store; cross-store atomicity is not attempted in v1.

### Positive Consequences

*   Each store runs at its native strength: Postgres for operational state + FKs + CHECKs, Neo4j for multi-hop temporal graph queries, OpenSearch for Hebrew text + vector retrieval, MinIO for write-once byte-level provenance.
*   OpenSearch can be wiped and rebuilt at any time from Neo4j + MinIO — removes OpenSearch from the backup-critical path.
*   UUID4 canonical IDs let any service mint identifiers offline (no central issuer, no race conditions on import) and make cross-store joins trivial.
*   Pydantic v2 → JSON Schema regeneration means the Python code and the published contracts cannot drift silently; CI catches it.
*   The Tier 1 / 2 / 3 source enum is encoded once (JSON Schema + Postgres CHECK + Neo4j property + OpenSearch mapping) so promotion-policy violations are structurally visible.

### Negative Consequences

*   **Two systems of record** (Neo4j for facts, Postgres for pipelines) means write ordering matters. Mitigation: documented `Postgres → Neo4j → OpenSearch` ordering, and Phase-1 acceptance test verifies a full round-trip.
*   **Neo4j community edition cannot enforce relationship-property existence** via constraints (that's an Enterprise feature). Mitigation: enforce `valid_from` / `valid_to` / `value` inside upsert templates, audit via the alignment smoke test.
*   **Four stores to operate** raises the operator surface area vs. a single Postgres deployment. Mitigated by docker-compose stack, a one-shot `migrator` container, and the `civic_clients` package providing uniform access.
*   **UUIDs everywhere** are less human-readable than INTs in logs. Mitigation: surrogate `BIGSERIAL id` still exists on Postgres rows for ops; domain logs always carry the UUID.
*   **OpenSearch and Neo4j consistency** is eventual, not transactional. Acceptable because OpenSearch is explicitly labelled a cache, and canonical reads go through Neo4j/Postgres.

## Alternatives considered — why rejected

*   **Option 2 (single-store Postgres).** Rejected: recursive CTEs over many-hop temporal edges (offices held across terms, committee membership windows) are expressive but expensive and brittle compared to Cypher. Phase 4 retrieval (graph + lexical + vector) would be significantly harder to scale. `pgvector` is fine for vectors, but combining graph, vector, and full-text in Postgres adds cognitive load and still requires a separate archive store.
*   **Option 3 (ArangoDB multi-model).** Rejected: the team and operators have direct experience with Neo4j + Postgres; ArangoDB would be a learning-curve tax with no clear win on Phase-1 acceptance. The multi-model promise does not extend to MinIO-style content-addressed archival.
*   **Option 4 (Elasticsearch instead of OpenSearch).** Rejected: Elastic's license changes (SSPL/Elastic License v2) create commercial and distribution uncertainty; OpenSearch is a drop-in Apache-2 fork and is already in the Phase-0 compose stack.
*   **Option 5 (INT PKs for cross-store joins via a central issuer).** Rejected: a central ID issuer is a single point of failure for offline and batch ingestion, and introduces a coordination round-trip on every insert. UUID4 lets any service mint identifiers without coordination.

## Evidence

*   Plan: [`docs/political_verifier_v_1_plan.md`](../political_verifier_v_1_plan.md) — source-tier policy (lines 31-65), node catalogue (lines 204-217), relationship catalogue (lines 219-230), Postgres table list (lines 232-241), OpenSearch index list (lines 243-246), canonical contracts (lines 248-308), archival rule (lines 311-320).
*   Human-readable companion: [`docs/DATA_MODEL.md`](../DATA_MODEL.md).
*   Archive URI spec: [`docs/conventions/archive-paths.md`](../conventions/archive-paths.md) (owned by Agent E in the same wave).
*   Phase-0 architecture: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).
