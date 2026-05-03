# Civic Proof IL — V2 Implementation Plan

## Purpose

This document defines the implementation plan for the next phase of `civic-proof-il`.

The goal of V2 is to **separate declarations from formal facts** while preserving the current V1 guarantees:

- official-source-first verification
- archived provenance
- conservative abstention
- no LLM authority over canonical facts
- human review for unresolved conflicts

The key architectural move is simple:

> A politician's statement is not a fact.
> It is a **declaration about the world** that must be stored separately from the formal records used to verify it.

---

## V2 Goal

Build a declaration-aware civic verification graph for Israeli politics that can distinguish between:

1. **What a politician said**
2. **What official records show**
3. **How the declaration relates to those records**

This allows the system to evaluate political claims without collapsing rhetoric into ground truth.

---

## Non-Goals

The following are explicitly out of scope for the first V2 milestones:

- inferring ideology, intent, or motivations
- scoring political sentiment
- social media-first ingestion
- municipal politics expansion
- broad policy interpretation
- replacing human review on ambiguous political claims
- using LLMs to resolve source conflicts

---

## Core Design Principle

Replace the idea of a single "ground truth" with a stricter internal model:

**Grounded official record with attributed declarations**

This means:

- formal facts come from Tier 1 official records
- declarations are stored independently
- verification judges the relationship between declarations and formal records
- public outputs should show both the claim and the record, not only a verdict label

---

## Current V1 Strengths to Preserve

The current codebase already has strong foundations:

- canonical JSON Schemas
- service-oriented domain layout
- archival and provenance handling
- entity resolution
- retrieval + verification separation
- reviewer workflow
- test pyramid across unit / integration / regression / e2e / benchmark

V2 should extend these seams, not replace them.

---

## Main V2 Deliverables

1. Add a first-class `Declaration` data model
2. Add persisted `AttributionEdge` records between declarations and formal objects
3. Add time-bounded `PositionTerm`
4. Add `GovernmentDecision`
5. Add `ElectionResult`
6. Refactor verification to support declaration-to-record judgments
7. Expand verdict taxonomy beyond supported / contradicted / insufficient
8. Add API and reviewer support for declaration-first flows

---

# 1. Architecture Changes

## 1.1 Existing Layers to Keep

Retain the current top-level structure:

- `data_contracts/jsonschemas/`
- `services/`
- `apps/`
- `tests/`

No new architectural layer is required.

## 1.2 New Conceptual Layers

V2 introduces three conceptual layers:

### A. Declaration layer
Represents utterances, quotes, and statements.

Examples:

- "I voted against the budget"
- "I served as Minister of Finance"
- "Our party won 10 seats"

### B. Formal record layer
Represents official facts from authoritative records.

Examples:

- vote events
- bill sponsorship
- role holdings
- committee memberships
- government decisions
- election results

### C. Attribution layer
Represents the relationship between the declaration and the formal record.

Examples:

- `supported_by`
- `contradicted_by`
- `overstates`
- `underspecifies`
- `time_scope_mismatch`
- `entity_ambiguous`

---

# 2. Data Contract Plan

## 2.1 Add New Schemas

Create the following files under:

```text
data_contracts/jsonschemas/
```

### New files

- `declaration.schema.json`
- `attribution_edge.schema.json`
- `position_term.schema.json`
- `government_decision.schema.json`
- `election_result.schema.json`

## 2.2 Reuse Existing Schemas

Do not duplicate or replace:

- `source_document.schema.json`
- `evidence_span.schema.json`
- `atomic_claim.schema.json`
- `verdict.schema.json`

These should remain part of the V2 flow.

## 2.3 Schema Responsibilities

### `declaration.schema.json`

Stores the utterance itself.

Required behavior:

- stores exact text
- stores language
- stores speaker
- stores utterance timestamp
- links to `SourceDocument`
- stores claim family
- stores checkability classification
- stores derived atomic claims without becoming a fact itself

### `attribution_edge.schema.json`

Stores auditable declaration-to-record relationships.

Required behavior:

- one persisted object per relationship
- can be reviewed or corrected by humans
- can attach evidence spans
- can store low-confidence or pending-review state

### `position_term.schema.json`

Models time-bounded office holdings.

Required behavior:

- person + office + start/end dates
- supports acting roles
- links to official source document
- allows verification of claims like "X was minister of Y"

### `government_decision.schema.json`

Models cabinet/government decisions.

Required behavior:

- decision number
- date
- title
- source document
- related entities if known

### `election_result.schema.json`

Models official election results.

Required behavior:

- election date
- party/list
- votes
- seats won
- threshold status
- source document

---

# 3. Domain Model Plan

## 3.1 Add Ontology Models

Add matching domain models under the ontology/model package currently used for schema drift checks.

Recommended files:

```text
packages/ontology/
  declaration.py
  attribution.py
  position_term.py
  government_decision.py
  election_result.py
```

## 3.2 Model Rules

- hand-written JSON Schemas remain canonical
- Pydantic models must match schemas
- schema drift checks must be extended to cover the new models

---

# 4. Graph Model Plan

## 4.1 New Node Types

Add the following graph node families:

- `Declaration`
- `PositionTerm`
- `GovernmentDecision`
- `ElectionResult`

If needed for auditability:

- `Attribution`

## 4.2 Existing Node Types to Reuse

Continue using existing formal entities such as:

- `Person`
- `Party`
- `Office`
- `Committee`
- `Bill`
- `VoteEvent`
- `MembershipTerm`
- `SourceDocument`
- `AtomicClaim`
- `EvidenceSpan`
- `Verdict`

## 4.3 New Relationships

Add or normalize relationships like:

- `(:Declaration)-[:SAID_BY]->(:Person)`
- `(:Declaration)-[:FROM_SOURCE]->(:SourceDocument)`
- `(:Declaration)-[:DERIVES]->(:AtomicClaim)`
- `(:Declaration)-[:REFERS_TO]->(:VoteEvent|:Bill|:PositionTerm|:GovernmentDecision|:ElectionResult)`
- `(:Person)-[:HAS_POSITION_TERM]->(:PositionTerm)`
- `(:PositionTerm)-[:ABOUT_OFFICE]->(:Office)`
- `(:GovernmentDecision)-[:CONCERNS]->(:Person|:Office|:Committee|:Party)`
- `(:ElectionResult)-[:FOR_PARTY]->(:Party)`

## 4.4 Graph Rule

Do not encode declarations directly as facts.

A declaration must always remain a separate object from the formal record it references.

---

# 5. Service-by-Service Implementation Plan

## 5.1 `services/claim_decomposition/`

### Add files

```text
services/claim_decomposition/
  declaration_classifier.py
  declaration_decomposer.py
  checkability_classifier.py
  claim_family_classifier.py
  temporal_scope_extractor.py
```

### Responsibilities

- always emit a `Declaration`
- emit zero or more `AtomicClaim`s
- classify declaration checkability
- classify claim family
- extract temporal scope hints
- preserve quoted span

### Important rule

Claim decomposition may propose formal atomic claims.
It may not create canonical facts.

---

## 5.2 `services/normalization/`

### Add files

```text
services/normalization/
  declaration_normalizer.py
  role_title_normalizer.py
  party_alias_history.py
  temporal_expression_normalizer.py
```

### Responsibilities

- canonicalize utterance text where needed
- normalize Hebrew and English office titles
- normalize party/list/faction aliases with date awareness
- normalize temporal language such as:
  - "currently"
  - "then"
  - "during that government"
  - "at the time"

---

## 5.3 `services/entity_resolution/`

### Add files

```text
services/entity_resolution/
  date_aware_resolver.py
  position_term_resolver.py
  declaration_entity_linker.py
```

### Responsibilities

- resolve people using claim-time context
- resolve party/list names using historical validity
- resolve offices using normalized titles
- support entity ambiguity outputs instead of forced linking

### Key requirement

Resolution must be date-aware.

A person/party/office match valid today is not necessarily valid at the time of the claim.

---

## 5.4 `services/ingestion/`

### Add or expand source families

```text
services/ingestion/
  elections/
  gov_il/
  declarations/
```

### Recommended subfiles

#### Elections

```text
services/ingestion/elections/
  fetcher.py
  parser.py
  normalizer.py
  upsert.py
  manifest.yaml
```

#### gov.il

```text
services/ingestion/gov_il/
  roles_fetcher.py
  roles_parser.py
  roles_normalizer.py
  decisions_fetcher.py
  decisions_parser.py
  decisions_normalizer.py
  upsert.py
  manifest.yaml
```

#### Declarations

```text
services/ingestion/declarations/
  fetcher.py
  parser.py
  normalizer.py
  upsert.py
```

### Ingestion priority

Implement in this order:

1. election results
2. gov.il roles / appointments
3. government decisions
4. declarations from transcripts and official statements

### Hard rule

Do not start V2 with broad social media ingestion.

That expands volume faster than truth quality.

---

## 5.5 `services/parsing/`

### Responsibilities

- source-specific deterministic extraction
- parse official tables/pages into structured rows
- keep parsing source-specific and testable

### Parsing targets

- election result tables
- gov.il role/appointment pages
- government decision pages
- transcript utterance boundaries

### Rule

Avoid LLM dependency in source parsers whenever deterministic parsing is feasible.

---

## 5.6 `services/retrieval/`

### Add files

```text
services/retrieval/
  declaration_retriever.py
  formal_record_retriever.py
  attribution_candidate_builder.py
```

### Responsibilities

#### `declaration_retriever.py`
Retrieve related declarations and linked material.

#### `formal_record_retriever.py`
Retrieve formal evidence candidates for atomic claims.

#### `attribution_candidate_builder.py`
Build candidate declaration-to-record mappings for verification.

### Retrieval split

V2 retrieval must explicitly separate:

- retrieval of declarations
- retrieval of formal records

Do not treat both as one flat evidence pool.

---

## 5.7 `services/verification/`

### Add files

```text
services/verification/
  declaration_verifier.py
  attribution_judge.py
  relation_type_rules.py
```

### Responsibilities

#### Stage A — alignment
Find which record the declaration appears to refer to.

#### Stage B — judgment
Decide the relationship between declaration and record.

### Required relation types

- `supported_by`
- `contradicted_by`
- `overstates`
- `underspecifies`
- `time_scope_mismatch`
- `entity_ambiguous`
- `not_checkable_against_record`

### Important change

Do not force every declaration into true/false/insufficient.
Political language often requires narrower relationship labels.

---

## 5.8 `services/review/`

### Add files

```text
services/review/
  declaration_review_repository.py
  review_reason_codes.py
  review_actions.py
```

### Responsibilities

- queue ambiguous declaration cases
- track human corrections to attribution edges
- store review reason codes
- support final reviewer confirmation/rejection

### Minimum review reason codes

- `tier1_conflict`
- `entity_ambiguity`
- `time_scope_ambiguity`
- `overgeneralized_declaration`
- `source_gap`

---

# 6. API Plan

## 6.1 Add API routes

Under `apps/api/`, add declaration-oriented routes.

Recommended files:

```text
apps/api/
  routes/
    declarations.py
    timelines.py
  schemas/
    declaration_requests.py
    declaration_responses.py
```

## 6.2 Recommended Endpoints

### `POST /declarations/ingest`

Purpose:
- create and store a declaration from text + source metadata

### `POST /declarations/{declaration_id}/verify`

Purpose:
- verify a stored declaration against formal records

### `GET /declarations/{declaration_id}`

Purpose:
- retrieve the declaration, linked claims, linked records, and current verification status

### `GET /entities/{entity_id}/timeline`

Purpose:
- show politician activity and declarations over time

## 6.3 API Output Rule

Responses should expose both:

- what was said
- what records show

Do not expose only a naked verdict label.

---

# 7. Worker Plan

Add background job entrypoints under `apps/worker/`.

Recommended files:

```text
apps/worker/
  jobs/
    ingest_elections.py
    ingest_govil_roles.py
    ingest_govil_decisions.py
    ingest_declarations.py
    recompute_attributions.py
```

## Job order

1. ingest elections
2. ingest gov.il roles
3. ingest gov.il decisions
4. ingest declarations
5. recompute declaration attributions

---

# 8. Reviewer UI Plan

## 8.1 Reviewer workflow changes

The reviewer UI should shift from claim-only review to declaration-first review.

Each review screen should show:

1. exact quote
2. source document + archive
3. parsed atomic claims
4. matched formal records
5. evidence spans
6. proposed relationship type
7. review reason if unresolved

## 8.2 Reviewer UX rule

Never lead with the verdict alone.

Lead with the quote and the record, then the relationship judgment.

This is critical for public trust in a political product.

---

# 9. Source Roadmap

## Phase A — High-confidence formal records

Implement first:

- official election results
- official government role/appointment pages
- official Knesset vote/membership/attendance data

## Phase B — Additional formal government records

Implement next:

- government decisions
- official ministerial releases that assert formal appointments/actions

## Phase C — Declarations

Implement after formal record backbone is stable:

- Knesset plenum transcripts
- committee transcripts
- official statements
- selected interviews with archived text

## Phase D — Optional later expansion

Only after declaration/formal separation is stable:

- social posts
- media paraphrases
- cross-source contradiction analysis

---

# 10. Verdict Taxonomy Expansion

V1-style true/false/insufficient is not enough for political discourse.

## Required output categories

- `supported`
- `contradicted`
- `unsupported`
- `not_checkable`
- `time_scope_missing`
- `time_scope_mismatch`
- `entity_ambiguous`
- `overgeneralized`
- `mixed`

## Rationale

Examples:

- "I voted against the bill" → likely `supported` / `contradicted`
- "I opposed the reform" → often `overgeneralized` or `not_checkable`
- "I served as minister" with missing date → `time_scope_missing`
- ambiguous party/list reference → `entity_ambiguous`

---

# 11. Testing Plan

## 11.1 Unit tests

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

## 11.2 Integration tests

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

## 11.3 Regression tests

Add:

```text
tests/regression/
  test_hebrew_alias_collisions.py
  test_party_rename_history.py
  test_time_scope_mismatch_cases.py
  test_overgeneralized_rhetoric_cases.py
  test_formal_action_vs_declaration_separation.py
```

## 11.4 E2E tests

Add:

```text
tests/e2e/
  test_declaration_to_verdict_flow.py
  test_entity_timeline_flow.py
```

## 11.5 Fixture directories

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

---

# 12. Milestones

## Milestone 1 — Declaration layer

### Deliverables

- `Declaration` schema + model
- `AttributionEdge` schema + model
- declaration ingestion path
- declaration-first decomposition output

### Success criteria

- quotes are stored independently from facts
- non-checkable declarations are still stored properly
- atomic claims derive from declarations instead of replacing them

---

## Milestone 2 — Position terms

### Deliverables

- `PositionTerm` schema + model
- gov.il role ingestion
- date-aware office verification

### Success criteria

- office-related claims can be checked against time-bounded role holdings

---

## Milestone 3 — Election records

### Deliverables

- `ElectionResult` schema + model
- election ingestion pipeline
- party/list continuity normalization

### Success criteria

- election seat/vote claims are checkable from Tier 1 records

---

## Milestone 4 — Government decisions

### Deliverables

- `GovernmentDecision` schema + model
- decision ingestion pipeline
- decision retrieval

### Success criteria

- government decision claims can be linked to official records

---

## Milestone 5 — Declaration-aware verification

### Deliverables

- declaration verifier
- attribution judgment
- expanded verdict taxonomy
- reviewer workflow for declaration-record mismatch

### Success criteria

- system can distinguish contradiction from overstatement, underspecification, and temporal mismatch

---

## Milestone 6 — Timeline and trust UX

### Deliverables

- entity timeline endpoint
- reviewer UI improvements
- evidence-first presentation

### Success criteria

- users can inspect what was said vs what the records show over time

---

# 13. Recommended PR Sequence

## PR 1 — Contracts + ontology

Add:

- new JSON Schemas
- new ontology/Pydantic models
- schema validation tests

## PR 2 — Declaration decomposition

Add:

- declaration decomposer
- checkability classifier
- claim family classifier
- temporal scope extraction

## PR 3 — gov.il positions

Add:

- role ingestion stack
- `PositionTerm`
- date-aware verification for offices

## PR 4 — election ingestion

Add:

- election fetch/parse/normalize/upsert
- list/faction continuity handling

## PR 5 — declaration verification

Add:

- declaration verifier
- attribution judge
- expanded relation taxonomy
- integration tests

## PR 6 — reviewer + API

Add:

- declaration routes
- timeline routes
- reviewer support for declaration-to-record review

## PR 7 — government decisions

Add:

- decisions ingestion
- decision retrieval
- decision-based verification support

---

# 14. What Not To Do Next

Do not spend the next cycle on:

- generic LLM quality improvements
- social media expansion
- multilingual summarization polish
- sentiment or persuasion scoring
- policy-position inference
- public ranking of politician truthfulness

These are downstream product ideas.
They are not the next architectural bottleneck.

The next bottleneck is **schema honesty**.

---

# 15. Definition of Done for V2 Core

V2 core is done when the system can:

1. ingest a politician declaration
2. store it as a first-class object
3. derive atomic claims from it
4. retrieve official records relevant to those claims
5. judge the declaration-to-record relationship
6. surface a reviewable, evidence-backed result
7. avoid collapsing rhetoric into canonical fact

---

# 16. Immediate First Files To Implement

If starting today in the IDE, begin with these exact files:

```text
data_contracts/jsonschemas/declaration.schema.json
data_contracts/jsonschemas/attribution_edge.schema.json
data_contracts/jsonschemas/position_term.schema.json
data_contracts/jsonschemas/government_decision.schema.json
data_contracts/jsonschemas/election_result.schema.json

packages/ontology/declaration.py
packages/ontology/attribution.py
packages/ontology/position_term.py
packages/ontology/government_decision.py
packages/ontology/election_result.py

services/claim_decomposition/declaration_decomposer.py
services/claim_decomposition/checkability_classifier.py
services/verification/declaration_verifier.py

tests/unit/test_declaration_schema.py
tests/integration/test_declaration_ingest_pipeline.py
```

---

# 17. Final Recommendation

Internally, stop calling the target "ground truth".

Use:

**grounded official record with attributed declarations**

That wording will force better modeling decisions and reduce the risk of category errors in a political system.

It is the right conceptual frame for Israel-focused political verification.
