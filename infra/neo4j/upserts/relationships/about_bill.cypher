// Upsert (:AtomicClaim)-[:ABOUT_BILL]->(:Bill).
// No relationship properties; template is a plain idempotent MERGE.
// Parameters: $claim_id, $bill_id.
MATCH (c:AtomicClaim {claim_id: $claim_id})
MATCH (b:Bill {bill_id: $bill_id})
MERGE (c)-[r:ABOUT_BILL]->(b)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN c.claim_id AS claim_id, b.bill_id AS bill_id;
