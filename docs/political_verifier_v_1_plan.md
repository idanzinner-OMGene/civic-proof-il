# Codex Task Spec: Political Verifier v1

## Objective
Build a **knowledge-graph-backed verifier for Israeli national political statements** that accepts a single statement, decomposes it into atomic claims, retrieves official evidence, and returns a conservative verdict with provenance.

## Product boundary
### In scope
- National Israeli political actors only:
  - MKs
  - ministers
  - deputy ministers
  - party leaders only when canonically resolvable
- Claim types:
  - `vote_cast`
  - `bill_sponsorship`
  - `office_held`
  - `committee_membership`
  - `committee_attendance`
  - `statement_about_formal_action` only if reducible to one of the above
- Single-statement verification
- Human review queue for ambiguous or high-risk cases

### Out of scope for v1
- Policy outcome claims
- Causal or impact claims
- General media fact-checking
- Live speech monitoring
- Summary auditing
- Non-officeholding spokespeople as canonical actors

## Non-negotiable rules
### Verification posture
- Default to **conservative abstention**
- Never issue a strong contradiction without Tier 1 evidence
- Unresolved Tier 1 conflicts must go to review
- No verdict without archived provenance

### Source tiers
#### Tier 1: canonical
- Official Knesset records
- Official gov.il role pages and releases
- Official government decision records on gov.il
- Official election-result sources

#### Tier 2: contextual
- Knesset research outputs
- Official oversight reports
- Similar official background material

#### Tier 3: discovery only
- Media
- Watchdogs
- Secondary aggregators
- OpenKnesset-like mirrors

### Promotion policy
A fact can enter canonical fact storage only if:
- it has at least one Tier 1 source,
- provenance is archived,
- time scope is normalized.

Text-derived facts with ambiguity require either:
- two Tier 1 supports, or
- one structured Tier 1 record plus one archived Tier 1 primary document.

## Implementation phases

### Phase 0: repo bootstrap
Deliver:
- monorepo scaffold
- docker-compose stack for Neo4j, OpenSearch, PostgreSQL, MinIO
- backend service skeleton
- migrations
- Makefile
- `.env.example`
- smoke tests

Acceptance criteria:
- `make up` starts all services
- `make test` passes
- `make seed-demo` loads sample data
- health endpoints are green

### Phase 1: canonical data model
Deliver:
- PostgreSQL schema for ingestion, verification, and review
- Neo4j constraints and upsert conventions
- OpenSearch index mappings
- object archive path conventions
- JSON schemas for contracts

Acceptance criteria:
- sample `Person`, `Office`, `AtomicClaim`, `EvidenceSpan`, and `Verdict` persist and query correctly

### Phase 2: first ingestion family
Build source adapters in this order:
1. people and roles
2. committees and memberships
3. plenum vote results
4. bill sponsorship
5. attendance

Deliver for each adapter:
- fetcher
- archival step
- parser
- normalizer
- KG upsert
- provenance link handling

Acceptance criteria:
- for a known politician, system can return office history, committee memberships, and at least one vote record

### Phase 3: atomic claim pipeline
Deliver:
- statement intake API
- rule-first decomposition
- ontology mapper
- entity resolution
- temporal normalizer
- checkability classifier
- schema validator

Acceptance criteria:
- statements like "X voted against bill Y in 2024" become structured claims
- vague claims are marked `non_checkable` or `insufficient_time_scope`

### Phase 4: retrieval and verification
Deliver:
- graph retrieval
- lexical plus vector retrieval over evidence archive
- deterministic reranker
- verdict engine
- abstention policy
- provenance bundle in response

Acceptance criteria:
- API returns normalized claim, verdict, confidence rubric, evidence spans, and uncertainty note

### Phase 5: review workflow
Deliver:
- reviewer queue
- conflict queue
- entity resolution correction flow
- evidence confirmation flow
- verdict override with audit log

Acceptance criteria:
- reviewer can approve, reject, relink, annotate, and escalate without silently mutating canonical facts

### Phase 6: hardening and evaluation
Deliver:
- benchmark set
- offline eval harness
- regression tests
- provenance completeness tests
- freshness monitoring

Acceptance criteria:
- every non-abstain verdict includes archived evidence
- regression suite protects against citation-free or overconfident verdicts

## Required repo structure
```text
political-verifier/
  apps/
    api/
    worker/
    reviewer_ui/
  packages/
    common/
    ontology/
    clients/
    prompts/
  infra/
    docker/
    migrations/
    neo4j/
    opensearch/
  data_contracts/
    jsonschemas/
  services/
    ingestion/
      gov_il/
      knesset/
      elections/
    parsing/
    normalization/
    entity_resolution/
    claim_decomposition/
    retrieval/
    verification/
    review/
    archival/
  tests/
    unit/
    integration/
    e2e/
    fixtures/
  scripts/
  docs/
```

## Core data model
### Neo4j nodes
- `Person`
- `Party`
- `Office`
- `Committee`
- `Bill`
- `VoteEvent`
- `AttendanceEvent`
- `MembershipTerm`
- `SourceDocument`
- `EvidenceSpan`
- `AtomicClaim`
- `Verdict`

### Neo4j relationships
- `(:Person)-[:MEMBER_OF {valid_from, valid_to}]->(:Party)`
- `(:Person)-[:HELD_OFFICE {valid_from, valid_to}]->(:Office)`
- `(:Person)-[:MEMBER_OF_COMMITTEE {valid_from, valid_to}]->(:Committee)`
- `(:Person)-[:SPONSORED]->(:Bill)`
- `(:Person)-[:CAST_VOTE {value}]->(:VoteEvent)`
- `(:SourceDocument)-[:HAS_SPAN]->(:EvidenceSpan)`
- `(:AtomicClaim)-[:ABOUT_PERSON]->(:Person)`
- `(:AtomicClaim)-[:ABOUT_BILL]->(:Bill)`
- `(:AtomicClaim)-[:SUPPORTED_BY]->(:EvidenceSpan)`
- `(:AtomicClaim)-[:CONTRADICTED_BY]->(:EvidenceSpan)`
- `(:Verdict)-[:EVALUATES]->(:AtomicClaim)`

### PostgreSQL tables
- `ingest_runs`
- `raw_fetch_objects`
- `parse_jobs`
- `normalized_records`
- `entity_candidates`
- `review_tasks`
- `review_actions`
- `verification_runs`
- `verdict_exports`

### OpenSearch indexes
- `source_documents`
- `evidence_spans`
- `claim_cache`

## Canonical contracts
### AtomicClaim
```json
{
  "claim_id": "uuid",
  "raw_text": "string",
  "normalized_text": "string",
  "claim_type": "vote_cast",
  "speaker_person_id": "uuid|null",
  "target_person_id": "uuid|null",
  "bill_id": "uuid|null",
  "committee_id": "uuid|null",
  "office_id": "uuid|null",
  "vote_value": "for|against|abstain|null",
  "time_scope": {
    "start": "ISO8601|null",
    "end": "ISO8601|null",
    "granularity": "day|month|year|term|unknown"
  },
  "checkability": "checkable|non_checkable|insufficient_time_scope|insufficient_entity_resolution",
  "created_at": "ISO8601"
}
```

### Verdict
```json
{
  "verdict_id": "uuid",
  "claim_id": "uuid",
  "status": "supported|contradicted|mixed|insufficient_evidence|non_checkable",
  "confidence": {
    "source_authority": 0,
    "directness": 0,
    "temporal_alignment": 0,
    "entity_resolution": 0,
    "cross_source_consistency": 0,
    "overall": 0
  },
  "summary": "string",
  "needs_human_review": true,
  "model_version": "string",
  "ruleset_version": "string",
  "created_at": "ISO8601"
}
```

### EvidenceSpan
```json
{
  "span_id": "uuid",
  "document_id": "uuid",
  "source_tier": 1,
  "source_type": "official_vote_record",
  "url": "string",
  "archive_uri": "string",
  "text": "string",
  "char_start": 0,
  "char_end": 120,
  "captured_at": "ISO8601"
}
```

## Service responsibilities
### Archival service
Responsibilities:
- fetch original source material
- store HTML, PDF, JSON, CSV, or text payloads
- hash content
- assign immutable archive URIs
- record fetch metadata

Rule:
- no verification-grade verdict may exist without an archived source object

### Ingestion service
Responsibilities:
- crawl official sources
- detect changes
- emit fetch and parse jobs
- normalize outputs
- upsert graph facts with provenance

Pattern:
- one adapter per source family
- one manifest per source family with cadence, trust tier, parser type, and entity hints

### Parsing service
Responsibilities:
- transform raw artifacts into normalized records

Outputs may include:
- person rows
- office rows
- committee rows
- membership rows
- vote rows
- sponsorship rows
- attendance rows

Rule:
- deterministic extraction first
- use LLM extraction only for text-heavy cases where structured parsing is not available

### Entity resolution service
Responsibilities:
- link names to canonical entities
- maintain alias table
- surface ambiguity

Resolution order:
1. official external IDs
2. exact normalized Hebrew match
3. curated aliases
4. transliteration normalization
5. fuzzy matching
6. LLM fallback for ambiguous ties only

### Claim decomposition service
Responsibilities:
- split statements into atomic claims
- map them to ontology types
- validate slot structure

Rule:
- rules first, LLM second, schema validation last

### Retrieval service
Responsibilities:
- graph retrieval for structured facts
- lexical and vector retrieval for evidence text
- merge and rerank results

Rule:
- no pure semantic-only retrieval path for ontology-backed claims

### Verification service
Responsibilities:
- compare normalized claims to retrieved evidence
- assign verdict
- compute rubric-based confidence
- decide abstain or escalate

Rule:
- final truth decision must remain deterministic or rule-governed in v1
- LLMs may summarize evidence, not decide truth by themselves

### Review service
Responsibilities:
- route risky cases
- collect reviewer actions
- preserve audit trail

## APIs to build
### POST `/claims/verify`
Input:
```json
{
  "statement": "string",
  "speaker_hint": "optional string",
  "language": "he|en",
  "strict_mode": true
}
```

Output:
```json
{
  "statement_id": "uuid",
  "claims": [
    {
      "claim_id": "uuid",
      "normalized_text": "string",
      "claim_type": "vote_cast",
      "verdict": "supported",
      "confidence_overall": 0.86,
      "needs_human_review": false,
      "time_scope": {},
      "evidence": [],
      "uncertainty_note": "string"
    }
  ]
}
```

### GET `/persons/{id}`
Return canonical person profile, aliases, party timeline, offices, and memberships.

### GET `/review/tasks`
Return queue of escalations.

### POST `/review/tasks/{id}/resolve`
Allow reviewers to approve, reject, relink, annotate, or escalate.

## Prompting policy
Use LLM prompting only where deterministic code is weaker.

### Allowed prompt categories
1. claim decomposition
2. temporal normalization
3. evidence summarization
4. reviewer-facing explanation

### Disallowed LLM roles
- canonical fact promotion without validation
- final conflict resolution between official records
- direct unvalidated database writes

## Review escalation rules
Route to human review when any of the following are true:
- Tier 1 sources conflict
- entity resolution confidence is below threshold
- time scope is weakly inferred
- evidence is indirect
- claim decomposition is uncertain
- only Tier 2 or Tier 3 evidence exists
- the claim targets a high-profile politician and machine verdict is contradiction

## Evaluation plan
Build a gold set stratified by:
- claim family
- ambiguity level
- actor prominence
- source type
- supported vs contradicted vs mixed vs abstain

Track:
- entity resolution accuracy
- temporal normalization accuracy
- claim typing accuracy
- evidence recall
- evidence precision
- verdict accuracy
- contradiction precision
- abstention correctness
- provenance completeness

## Eight-week execution schedule
### Week 1
- scaffold repo
- compose stack
- migrations
- env and docs
- smoke tests

### Week 2
- archival layer
- source manifests
- people and roles adapter

### Week 3
- committee and membership ingestion
- graph upsert logic
- alias table

### Week 4
- vote ingestion
- sponsorship ingestion
- fixtures and parsers

### Week 5
- claim decomposition
- entity resolution
- temporal normalization
- checkability classification

### Week 6
- retrieval layer
- OpenSearch indexing
- deterministic reranker
- first verdict engine

### Week 7
- review queue
- conflict handling
- audit logging
- benchmark harness

### Week 8
- regression tests
- hardening
- demo scenarios
- deployment docs

## Initial Codex ticket list
1. Create monorepo scaffold and local infra.
2. Add Docker services for Neo4j, OpenSearch, PostgreSQL, and MinIO.
3. Add database migrations and constraints.
4. Implement archive client with content hashing.
5. Implement source adapter for people and roles.
6. Implement committees and memberships adapter.
7. Implement vote-event adapter.
8. Implement bill sponsorship adapter.
9. Implement attendance adapter.
10. Add canonical JSON schemas and validators.
11. Implement rule-based claim decomposition for the main templates.
12. Add LLM fallback decomposition behind schema validation.
13. Implement entity resolver with alias handling.
14. Implement graph retrieval.
15. Implement evidence indexing and lexical plus vector retrieval.
16. Implement deterministic verdict engine with abstention rules.
17. Implement `/claims/verify`.
18. Implement review queue and human override logging.
19. Add end-to-end tests for at least 25 gold examples.
20. Write deployment and operator docs.

## Definition of done for v1
v1 is done when the system can, for a single statement:
- extract a valid atomic claim,
- resolve actor and referenced entities,
- retrieve official evidence,
- return a conservative verdict,
- cite archived provenance,
- abstain on ambiguous cases,
- route risky cases to review.

