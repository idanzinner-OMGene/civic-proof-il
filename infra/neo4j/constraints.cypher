// Phase 1 domain constraints for the Neo4j schema.
//
// References docs/political_verifier_v_1_plan.md lines 204-217 (nodes).
// All statements are idempotent (IF NOT EXISTS) so `cypher-shell < constraints.cypher`
// can be re-applied safely on every migrator run.
//
// For each of the 12 domain nodes we enforce ONE declarative invariant:
//   Unique business key (<entity>_id)
//
// The 12 nodes covered here are:
//   Person, Party, Office, Committee, Bill, VoteEvent, AttendanceEvent,
//   MembershipTerm, SourceDocument, EvidenceSpan, AtomicClaim, Verdict.
//
// Property-existence constraints (both node and relationship) are Enterprise-only
// in Neo4j 5. On Community Edition those invariants are enforced in the
// parameterized MERGE templates under `infra/neo4j/upserts/` and
// `infra/neo4j/upserts/relationships/`, which refuse to MERGE a node or edge
// without its required properties via an explicit WHERE filter on $params.
// See `infra/neo4j/README.md` for the rationale and enforcement contract.

// ---- Person ---------------------------------------------------------------
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;

// ---- Party ----------------------------------------------------------------
CREATE CONSTRAINT party_id_unique IF NOT EXISTS
FOR (p:Party) REQUIRE p.party_id IS UNIQUE;

// ---- Office ---------------------------------------------------------------
CREATE CONSTRAINT office_id_unique IF NOT EXISTS
FOR (o:Office) REQUIRE o.office_id IS UNIQUE;

// ---- Committee ------------------------------------------------------------
CREATE CONSTRAINT committee_id_unique IF NOT EXISTS
FOR (c:Committee) REQUIRE c.committee_id IS UNIQUE;

// ---- Bill -----------------------------------------------------------------
CREATE CONSTRAINT bill_id_unique IF NOT EXISTS
FOR (b:Bill) REQUIRE b.bill_id IS UNIQUE;

// ---- VoteEvent ------------------------------------------------------------
CREATE CONSTRAINT vote_event_id_unique IF NOT EXISTS
FOR (v:VoteEvent) REQUIRE v.vote_event_id IS UNIQUE;

// ---- AttendanceEvent ------------------------------------------------------
CREATE CONSTRAINT attendance_event_id_unique IF NOT EXISTS
FOR (a:AttendanceEvent) REQUIRE a.attendance_event_id IS UNIQUE;

// ---- MembershipTerm -------------------------------------------------------
CREATE CONSTRAINT membership_term_id_unique IF NOT EXISTS
FOR (m:MembershipTerm) REQUIRE m.membership_term_id IS UNIQUE;

// ---- SourceDocument -------------------------------------------------------
CREATE CONSTRAINT source_document_id_unique IF NOT EXISTS
FOR (s:SourceDocument) REQUIRE s.document_id IS UNIQUE;

// ---- EvidenceSpan ---------------------------------------------------------
CREATE CONSTRAINT evidence_span_id_unique IF NOT EXISTS
FOR (e:EvidenceSpan) REQUIRE e.span_id IS UNIQUE;

// ---- AtomicClaim ----------------------------------------------------------
CREATE CONSTRAINT atomic_claim_id_unique IF NOT EXISTS
FOR (c:AtomicClaim) REQUIRE c.claim_id IS UNIQUE;

// ---- Verdict --------------------------------------------------------------
CREATE CONSTRAINT verdict_id_unique IF NOT EXISTS
FOR (v:Verdict) REQUIRE v.verdict_id IS UNIQUE;

// ---- V2 nodes -------------------------------------------------------------

// ---- Declaration ----------------------------------------------------------
CREATE CONSTRAINT declaration_id_unique IF NOT EXISTS
FOR (d:Declaration) REQUIRE d.declaration_id IS UNIQUE;

// ---- PositionTerm ---------------------------------------------------------
CREATE CONSTRAINT position_term_id_unique IF NOT EXISTS
FOR (p:PositionTerm) REQUIRE p.position_term_id IS UNIQUE;

// ---- GovernmentDecision ---------------------------------------------------
CREATE CONSTRAINT government_decision_id_unique IF NOT EXISTS
FOR (g:GovernmentDecision) REQUIRE g.government_decision_id IS UNIQUE;

// ---- ElectionResult -------------------------------------------------------
CREATE CONSTRAINT election_result_id_unique IF NOT EXISTS
FOR (e:ElectionResult) REQUIRE e.election_result_id IS UNIQUE;
