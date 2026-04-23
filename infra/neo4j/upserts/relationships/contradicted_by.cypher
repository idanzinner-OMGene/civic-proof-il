// Upsert (:AtomicClaim)-[:CONTRADICTED_BY]->(:EvidenceSpan).
// No relationship properties; template is a plain idempotent MERGE.
// Parameters: $claim_id, $span_id.
MATCH (c:AtomicClaim {claim_id: $claim_id})
MATCH (e:EvidenceSpan {span_id: $span_id})
MERGE (c)-[r:CONTRADICTED_BY]->(e)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN c.claim_id AS claim_id, e.span_id AS span_id;
