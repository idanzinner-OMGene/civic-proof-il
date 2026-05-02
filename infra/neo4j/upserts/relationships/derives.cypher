// Upsert (:Declaration)-[:DERIVES]->(:AtomicClaim).
// Parameters: $declaration_id, $claim_id.
MATCH (d:Declaration {declaration_id: $declaration_id})
MATCH (c:AtomicClaim {claim_id: $claim_id})
MERGE (d)-[r:DERIVES]->(c)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN d.declaration_id AS declaration_id, c.claim_id AS claim_id;
