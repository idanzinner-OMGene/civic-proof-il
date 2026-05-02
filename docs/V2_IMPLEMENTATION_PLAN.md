# V2_IMPLEMENTATION_PLAN.md — civic-proof-il

> **Purpose:** Concrete implementation plan for the next phase of `civic-proof-il`, written to match the repo’s existing documentation style and architecture constraints.
>
> **Scope:** Add a first-class declaration layer and extend formal records beyond Knesset-only data, while preserving v1 verifier invariants.
>
> **Read this with:** `docs/AGENT_GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/PROJECT_STATUS.md`, and `docs/political_verifier_v_1_plan.md`.

---

## 1) Problem statement

`civic-proof-il` v1 is already a disciplined political verifier. It is conservative, provenance-first, and rule-driven:

- Tier 1 evidence is required for verdicts.
- Tier 1 conflicts go to human review.
- No verdict is produced without archived provenance.
- LLMs assist decomposition, normalization, and summarization only.
- Canonical facts are not written by LLMs.

That foundation is correct.

The next gap is **not** “more AI” and **not** “more retrieval.” The gap is the data model.

Today, the system is strongest at verifying formal political actions such as:

- votes,
- attendance,
- committee membership,
- office-related claims that can be reduced to existing records.

The next step is to explicitly separate:

1. **what a politician said**,
2. **what official records show**,
3. **how the system relates the two**.

Without this separation, the graph risks collapsing political declarations into facts.

---

## 2) Goals

### Primary goals

- Add a **first-class `Declaration` object** to the canonical data model.
- Preserve v1 verification invariants and source-tier rules.
- Extend formal records to support:
  - `PositionTerm`
  - `GovernmentDecision`
  - `ElectionResult`
- Add explicit attribution / relation semantics between declarations and formal records.
- Keep Neo4j as the source of domain facts, Postgres for pipelines/queues, OpenSearch for search/cache, MinIO for immutable archive.

### Non-goals

- No broad social media ingestion in this phase.
- No ideology / intent inference.
- No generalized “political truth engine.”
- No replacement of v1 verdict logic with LLM reasoning.
- No move away from hand-written canonical JSON Schemas.

---

## 3) Core design decision

### New internal framing

Do **not** use “ground truth” internally as the main design concept.

Use:

- **grounded official record**
- **attributed declaration**
- **declaration-to-record relationship**

Reason: in political systems, especially in Israel, there is often no single universal ground truth object. There are:

- official records of formal actions,
- official but lagging or conflicting records,
- declarations about those records,
- narratives built on top of those records.

The system should represent these separately.

---

## 4) Architectural invariants to preserve

These are already established in the repo and **must remain true**:

- **Conservative abstention by default**
- **Tier 1 conflicts => human review**
- **No verdict without archived provenance**
- **Rule-first verification**
- **LLMs cannot create canonical facts**
- **Hand-written JSON Schemas are canonical**
- **UUID business keys remain the stable identity layer**
- **Neo4j remains the domain store**
- **Postgres remains operational/pipeline storage**
- **OpenSearch remains search/index/cache**
- **Archive URIs remain content-addressed and immutable**

Do not compromise any of these while implementing v2.

---

## 5) Target v2 data model

## 5.1 New entities

Add the following canonical objects:

- `Declaration`
- `AttributionEdge`
- `PositionTerm`
- `GovernmentDecision`
- `ElectionResult`

## 5.2 Keep and reuse existing objects

Reuse existing canonical objects wherever possible:

- `Person`
- `Party`
- `Office`
- `Committee`
- `Bill`
- `VoteEvent`
- `AttendanceEvent`
- `MembershipTerm`
- `AtomicClaim`
- `EvidenceSpan`
- `SourceDocument`
- `Verdict`

Important: `SourceDocument` already exists and should remain the shared provenance object.

---

## 6) Canonical schema changes

Add these files under:

```text
data_contracts/jsonschemas/
```

### New schema files

```text
declaration.schema.json
attribution_edge.schema.json
position_term.schema.json
government_decision.schema.json
election_result.schema.json
```

### Schema intent

#### `declaration.schema.json`

Represents an utterance as an object in its own right.

Minimum fields:

- `declaration_id`
- `speaker_person_id`
- `utterance_text`
- `utterance_language`
- `utterance_time`
- `source_document_id`
- `source_kind`
- `quoted_span`
- `canonicalized_text`
- `claim_family`
- `checkability`
- `derived_atomic_claim_ids`
- `created_at`

#### `attribution_edge.schema.json`

Persists the judgment connecting a declaration to a formal record or claim.

Minimum fields:

- `attribution_id`
- `from_declaration_id`
- `to_object_id`
- `to_object_type`
- `relation_type`
- `evidence_span_ids`
- `confidence_band`
- `review_status`
- `created_at`

#### `position_term.schema.json`

Time-bounded role holding.

Minimum fields:

- `position_term_id`
- `person_id`
- `office_id`
- `appointing_body`
- `valid_from`
- `valid_to`
- `is_acting`
- `source_document_id`
- `created_at`

#### `government_decision.schema.json`

Formal government decision record.

Minimum fields:

- `government_decision_id`
- `decision_number`
- `government_number`
- `decision_date`
- `title`
- `summary`
- `issuing_body`
- `source_document_id`
- `created_at`

#### `election_result.schema.json`

Formal election result record.

Minimum fields:

- `election_result_id`
- `election_date`
- `list_party_id`
- `votes`
- `seats_won`
- `vote_share`
- `passed_threshold`
- `source_document_id`
- `created_at`

---

## 7) Neo4j graph changes

Extend the graph rather than rewriting it.

### New node labels

- `Declaration`
- `PositionTerm`
- `GovernmentDecision`
- `ElectionResult`

Optional:
- `Attribution` as a node if auditing relation history becomes cumbersome as plain edges.

### New / normalized relationships

- `(:Declaration)-[:SAID_BY]->(:Person)`
- `(:Declaration)-[:FROM_SOURCE]->(:SourceDocument)`
- `(:Declaration)-[:DERIVES]->(:AtomicClaim)`
- `(:Declaration)-[:REFERS_TO]->(:VoteEvent|:Bill|:PositionTerm|:GovernmentDecision|:ElectionResult)`
- `(:Person)-[:HAS_POSITION_TERM]->(:PositionTerm)`
- `(:PositionTerm)-[:ABOUT_OFFICE]->(:Office)`
- `(:GovernmentDecision)-[:CONCERNS]->(:Person|:Office|:Committee|:Party)`
- `(:ElectionResult)-[:FOR_PARTY]->(:Party)`

### Important rule

A `Declaration` is **not** a fact node.

It is a source-bearing political utterance that may produce zero or more atomic claims and may or may not align with formal records.

---

## 8) Service-by-service implementation plan

Use the existing service layout under:

```text
services/
```

Do not create a parallel architecture.

### 8.1 `services/claim_decomposition/`

Add:

```text
declaration_classifier.py
declaration_decomposer.py
checkability_classifier.py
claim_family_classifier.py
temporal_scope_extractor.py
```

#### Responsibilities

- Always emit a `Declaration`.
- Emit zero or more `AtomicClaim`s derived from the declaration.
- Classify whether the utterance is:
  - `checkable_formal_action`
  - `partially_checkable`
  - `not_checkable`
  - `insufficient_time_scope`
  - `insufficient_entity_resolution`
- Extract temporal cues from the utterance.
- Preserve quoted spans.

#### Hard rule

`claim_decomposition` may propose structured claims.

It may **not** create canonical facts.

---

### 8.2 `services/normalization/`

Add:

```text
declaration_normalizer.py
role_title_normalizer.py
party_alias_history.py
temporal_expression_normalizer.py
```

#### Responsibilities

- Normalize declaration text for search and decomposition.
- Normalize Hebrew / English office titles.
- Resolve party/list/faction aliases with time awareness.
- Normalize temporal expressions:
  - “at the time”
  - “then”
  - “currently”
  - “during the previous government”
  - etc.

This is a critical area for Israeli political data quality.

---

### 8.3 `services/entity_resolution/`

Add:

```text
date_aware_resolver.py
position_term_resolver.py
declaration_entity_linker.py
```

#### Responsibilities

- Resolve person / party / office identities with `as_of_date`.
- Prefer identities valid at claim time, not retrieval time.
- Support office and party continuity across name and coalition/faction changes.
- Link declaration surfaces to canonical entities without over-committing in ambiguous cases.

#### Hard rule

Date awareness is not optional in v2.

---

### 8.4 `services/ingestion/`

Expand the existing ingestion layout.

Recommended additions:

```text
services/ingestion/
  elections/
    fetcher.py
    parser.py
    normalizer.py
    upsert.py
    manifest.yaml
  gov_il/
    roles_fetcher.py
    roles_parser.py
    roles_normalizer.py
    decisions_fetcher.py
    decisions_parser.py
    decisions_normalizer.py
    upsert.py
    manifest.yaml
  declarations/
    fetcher.py
    parser.py
    normalizer.py
    upsert.py
```

#### Source priority for this phase

1. official election results
2. official gov.il role / appointment pages
3. official government decisions
4. declarations from Knesset transcripts / official releases

#### Explicit non-goal for this phase

No broad social media ingestion.

---

### 8.5 `services/parsing/`

Use for deterministic source-specific extraction.

Responsibilities:

- parse official role pages into `PositionTerm`
- parse decision pages into `GovernmentDecision`
- parse election sources into `ElectionResult`
- parse transcript sources into `ParsedUtterance`

Keep parsing deterministic wherever possible.

---

### 8.6 `services/retrieval/`

Add:

```text
declaration_retriever.py
formal_record_retriever.py
attribution_candidate_builder.py
```

#### Retrieval split

Two retrieval modes should exist:

1. **formal-record retrieval**
2. **declaration retrieval**

A declaration-centric verification flow should retrieve:

- candidate formal records,
- prior declarations by the same speaker on the same topic,
- relevant source documents,
- supporting `EvidenceSpan`s.

---

### 8.7 `services/verification/`

Add:

```text
declaration_verifier.py
attribution_judge.py
relation_type_rules.py
```

#### Verification should become a two-stage process

### Stage A — record alignment

Determine whether the declaration refers to:

- a vote,
- bill sponsorship,
- office holding,
- committee membership,
- attendance,
- government decision,
- election result,
- or something that cannot be reduced to a formal record.

### Stage B — relation judgment

Return one of:

- `supported_by`
- `contradicted_by`
- `overstates`
- `underspecifies`
- `time_scope_mismatch`
- `entity_ambiguous`
- `not_checkable_against_record`

This is more useful than forcing everything into true / false / insufficient.

---

### 8.8 `services/review/`

Add:

```text
declaration_review_repository.py
review_reason_codes.py
review_actions.py
```

#### Reviewer queue reasons

- `tier1_conflict`
- `entity_ambiguity`
- `time_scope_ambiguity`
- `overgeneralized_declaration`
- `source_gap`

#### Reviewer actions

- bind canonical record
- split declaration into smaller claims
- fix time scope
- mark rhetorical / non-checkable
- confirm / reject attribution relation

---

## 9) App-level changes

Use the existing apps under:

```text
apps/
```

### 9.1 `apps/api`

Add routes for declaration-first workflows.

Recommended route files:

```text
apps/api/routes/declarations.py
apps/api/routes/timelines.py
apps/api/schemas/declaration_requests.py
apps/api/schemas/declaration_responses.py
```

### Suggested endpoints

#### `POST /declarations/ingest`

Create and store a `Declaration`, decompose it, and return derived atomic claim ids.

#### `POST /declarations/{declaration_id}/verify`

Run declaration verification and return attribution relations plus explanation metadata.

#### `GET /declarations/{declaration_id}`

Return declaration object + linked source + derived claims + linked formal records.

#### `GET /entities/{entity_id}/timeline`

Return a politician timeline combining:

- declarations,
- offices held,
- memberships,
- votes,
- government decisions,
- election results.

---

### 9.2 `apps/worker`

Add jobs:

```text
apps/worker/jobs/
  ingest_elections.py
  ingest_govil_roles.py
  ingest_govil_decisions.py
  ingest_declarations.py
  recompute_attributions.py
```

### 9.3 `apps/reviewer_ui`

Add declaration-focused review screens.

Each review page should show, in order:

1. exact quote / utterance
2. source metadata + archive URI
3. parsed atomic claims
4. matched formal records
5. evidence spans
6. relation judgment
7. review controls

The reviewer UI should make it visually obvious that:

- the declaration is one object,
- the official record is another object,
- the judgment connects them.

---

## 10) Suggested package / model files

If ontology models are under `packages/ontology/`, add:

```text
packages/ontology/
  declaration.py
  attribution.py
  position_term.py
  government_decision.py
  election_result.py
```

### Keep the repo’s current contract pattern

- Hand-written JSON Schemas are canonical.
- Pydantic models mirror them.
- Drift checks should be extended to cover the new objects.
- `populate_by_name=True` conventions should remain intact where already used.

---

## 11) Source rollout order

Implementation order matters.

### Phase A — lowest ambiguity / highest leverage

- official election results
- official gov.il role / appointment pages
- existing Knesset formal records

### Phase B — still formal, somewhat messier

- official government decisions
- official ministerial releases asserting formal appointments or decisions

### Phase C — declarations

- plenum transcripts
- committee transcripts
- official quoted statements

### Not in this phase

- broad media ingest
- broad social platform ingest
- opinion content

---

## 12) Test plan

Extend the existing structure under:

```text
tests/
```

### 12.1 Unit

Add:

```text
tests/unit/
  test_declaration_schema.py
  test_attribution_edge_schema.py
  test_position_term_schema.py
  test_government_decision_schema.py
  test_election_result_schema.py
  test_declaration_decomposer.py
  test_checkability_classifier.py
  test_role_title_normalizer.py
  test_date_aware_entity_resolver.py
  test_relation_type_rules.py
```

### 12.2 Integration

Add:

```text
tests/integration/
  test_ingest_elections_pipeline.py
  test_ingest_govil_roles_pipeline.py
  test_ingest_govil_decisions_pipeline.py
  test_declaration_ingest_pipeline.py
  test_verify_declaration_vs_vote_event.py
  test_verify_declaration_vs_position_term.py
```

### 12.3 Regression

Add:

```text
tests/regression/
  test_hebrew_alias_collisions.py
  test_party_rename_history.py
  test_time_scope_mismatch_cases.py
  test_overgeneralized_rhetoric_cases.py
  test_formal_action_vs_declaration_separation.py
```

### 12.4 E2E

Add:

```text
tests/e2e/
  test_declaration_to_verdict_flow.py
  test_entity_timeline_flow.py
```

### 12.5 Fixtures

Add:

```text
tests/fixtures/
  declarations/
  elections/
  govil_roles/
  govil_decisions/
  ambiguous_entities/
  rhetorical_claims/
```

### Important test constraint

Keep using the repo’s real-data / record-replay posture for external-source tests. Do not slip into synthetic fake-source behavior where it matters for pipeline correctness.

---

## 13) Milestones

## Milestone 1 — Declaration layer

### Deliverables

- `Declaration` schema + model
- `AttributionEdge` schema + model
- declaration-first decomposition
- declaration ingest API
- schema / unit tests

### Exit criteria

- political utterances are stored independently from verdicts
- declaration decomposition produces zero or more atomic claims
- non-checkable statements still exist as declarations

---

## Milestone 2 — Position terms

### Deliverables

- `PositionTerm` schema + model
- gov.il role ingestion
- date-aware resolution for office claims
- integration tests

### Exit criteria

- “served as minister / deputy minister / chair” claims are verified against time-bounded holdings, not static labels

---

## Milestone 3 — Election results

### Deliverables

- `ElectionResult` schema + model
- official election ingestion
- party/list continuity normalization
- retrieval integration

### Exit criteria

- seat / vote / threshold claims are checkable against Tier 1 election records

---

## Milestone 4 — Government decisions

### Deliverables

- `GovernmentDecision` schema + model
- decision ingestion pipeline
- retrieval + evidence linking

### Exit criteria

- government-decision claims are no longer shoehorned into bill/vote logic

---

## Milestone 5 — Declaration-to-record relation judgments

### Deliverables

- `DeclarationVerifier`
- attribution rules
- expanded relation taxonomy
- reviewer workflow integration

### Exit criteria

- the system can return:
  - supported,
  - contradicted,
  - overstates,
  - underspecifies,
  - time scope mismatch,
  - entity ambiguous,
  - not checkable.

---

## 14) PR sequence

Recommended order of implementation:

### PR 1

- add new JSON Schemas
- add matching ontology models
- extend schema drift checks
- add schema unit tests

### PR 2

- add `DeclarationDecomposer`
- add declaration/checkability/claim-family classification
- update decomposition outputs to return declaration + atomic claims

### PR 3

- add gov.il role ingestion
- add `PositionTerm`
- add time-aware office resolution
- add integration tests

### PR 4

- add election ingestion
- add party/list continuity handling
- add integration + regression tests

### PR 5

- add declaration verification
- add attribution judgments
- add reviewer/API support

### PR 6

- add government decision ingestion
- connect decision claims to formal verification flow

This sequence is designed to force schema discipline before feature sprawl.

---

## 15) Risks and mitigations

### Risk 1 — schema drift and duplicated truth semantics

**Risk:** `Declaration` becomes a loose wrapper around `AtomicClaim` and duplicates fact logic.

**Mitigation:** enforce a hard distinction:
- `Declaration` = utterance
- `AtomicClaim` = structured check candidate
- formal record = canonical official record

### Risk 2 — time-insensitive entity resolution

**Risk:** system resolves parties / offices using present-day identity only.

**Mitigation:** require `as_of_date` support for relevant entity-resolution paths.

### Risk 3 — source sprawl before source trust is stable

**Risk:** broad declaration/source ingestion before formal sources are complete.

**Mitigation:** keep source rollout order strict. Formal records first.

### Risk 4 — verdict oversimplification

**Risk:** political rhetoric gets forced into true/false.

**Mitigation:** expand relation taxonomy and show reviewer-facing reason codes.

### Risk 5 — reviewer confusion

**Risk:** UI shows verdict first and makes the system look partisan.

**Mitigation:** show declaration, source, and formal record before the relation judgment.

---

## 16) What not to do

Do **not** do the following in this phase:

- do not ingest broad social media streams
- do not attempt sentiment / ideology / intent classification
- do not replace rule-first verification with LLM-based verdicting
- do not let media summaries become canonical facts
- do not treat declaration text as equivalent to official records
- do not optimize for benchmark perfection on a narrow gold set

---

## 17) First files to create

Recommended first implementation slice:

```text
data_contracts/jsonschemas/declaration.schema.json
data_contracts/jsonschemas/attribution_edge.schema.json
packages/ontology/declaration.py
packages/ontology/attribution.py
services/claim_decomposition/declaration_decomposer.py
services/verification/declaration_verifier.py
tests/unit/test_declaration_schema.py
tests/integration/test_declaration_ingest_pipeline.py
```

This is the minimum slice that forces the project to stop conflating utterances with facts.

---

## 18) Definition of done for v2 core

The v2 core is done when all of the following are true:

- A politician’s statement is stored as a first-class declaration.
- The system can derive atomic claims from that declaration without collapsing it into fact.
- Official records for offices, elections, and government decisions are ingested and queryable.
- Verification outputs describe the relationship between declaration and record.
- Time-bounded role claims work correctly.
- Reviewer UI can inspect declaration, evidence, and relation judgment separately.
- All of the above preserve v1 source-tier and provenance invariants.

---

## 19) Suggested doc placement

Recommended final repo path:

```text
docs/V2_IMPLEMENTATION_PLAN.md
```

Optional follow-up docs after implementation begins:

```text
docs/adr/0004-declaration-layer.md
docs/adr/0005-date-aware-entity-resolution.md
docs/adr/0006-declaration-to-record-relations.md
```

---

## 20) Immediate next action

Implement **PR 1** first:

1. add the five new schemas,
2. add matching ontology models,
3. extend drift checks,
4. add schema validation tests.

Do not start with ingestion.

The schema split is the real project decision.