// Enrich a VoteEvent node with its bill_id and create the ABOUT_BILL edge.
// Called by scripts/enrich_vote_bills.py after the votes + sponsorships adapters run.
//
// Parameters:
//   $vote_event_id  — UUID string (uuid5 of "knesset_vote:{VoteID}")
//   $bill_id        — UUID string (uuid5 of "knesset_bill:{BillID}"), must not be NULL
//   $occurred_at    — ISO-8601 datetime string or NULL
//   $vote_type      — string or NULL
//
// Semantics:
//   MATCH the VoteEvent (it must already exist from the votes adapter pass).
//   Set bill_id + occurred_at + vote_type on the node.
//   MATCH the Bill (it must already exist from the sponsorships/bill_initiators pass).
//   MERGE the ABOUT_BILL relationship (idempotent).
MATCH (ve:VoteEvent {vote_event_id: $vote_event_id})
SET ve.bill_id     = $bill_id,
    ve.occurred_at = CASE WHEN $occurred_at IS NULL THEN ve.occurred_at ELSE datetime($occurred_at) END,
    ve.vote_type   = coalesce($vote_type, ve.vote_type)
WITH ve
MATCH (b:Bill {bill_id: $bill_id})
MERGE (ve)-[r:ABOUT_BILL]->(b)
ON CREATE SET r.created_at = datetime()
ON MATCH  SET r.updated_at = datetime()
RETURN ve.vote_event_id AS vote_event_id, b.bill_id AS bill_id;
