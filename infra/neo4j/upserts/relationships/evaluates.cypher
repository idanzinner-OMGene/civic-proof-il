// Upsert (:Verdict)-[:EVALUATES]->(:AtomicClaim).
// No relationship properties; template is a plain idempotent MERGE.
// Parameters: $verdict_id, $claim_id.
MATCH (v:Verdict {verdict_id: $verdict_id})
MATCH (c:AtomicClaim {claim_id: $claim_id})
MERGE (v)-[r:EVALUATES]->(c)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN v.verdict_id AS verdict_id, c.claim_id AS claim_id;
