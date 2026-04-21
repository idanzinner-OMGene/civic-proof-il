// Phase 0 placeholder constraints.
// Real domain constraints (Person, Party, Office, Committee, Bill, VoteEvent, etc.)
// arrive in Phase 1 per docs/political_verifier_v_1_plan.md.
//
// All statements must be idempotent (IF NOT EXISTS).

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;

CREATE CONSTRAINT party_id_unique IF NOT EXISTS
FOR (p:Party) REQUIRE p.party_id IS UNIQUE;

CREATE CONSTRAINT office_id_unique IF NOT EXISTS
FOR (o:Office) REQUIRE o.office_id IS UNIQUE;

CREATE CONSTRAINT committee_id_unique IF NOT EXISTS
FOR (c:Committee) REQUIRE c.committee_id IS UNIQUE;

CREATE CONSTRAINT bill_id_unique IF NOT EXISTS
FOR (b:Bill) REQUIRE b.bill_id IS UNIQUE;

CREATE CONSTRAINT source_document_id_unique IF NOT EXISTS
FOR (s:SourceDocument) REQUIRE s.document_id IS UNIQUE;

CREATE CONSTRAINT atomic_claim_id_unique IF NOT EXISTS
FOR (c:AtomicClaim) REQUIRE c.claim_id IS UNIQUE;

CREATE CONSTRAINT verdict_id_unique IF NOT EXISTS
FOR (v:Verdict) REQUIRE v.verdict_id IS UNIQUE;
