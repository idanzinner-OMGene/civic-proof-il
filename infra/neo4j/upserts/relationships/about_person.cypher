// Upsert (:AtomicClaim)-[:ABOUT_PERSON]->(:Person).
// No relationship properties; template is a plain idempotent MERGE.
// Parameters: $claim_id, $person_id.
MATCH (c:AtomicClaim {claim_id: $claim_id})
MATCH (p:Person {person_id: $person_id})
MERGE (c)-[r:ABOUT_PERSON]->(p)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN c.claim_id AS claim_id, p.person_id AS person_id;
