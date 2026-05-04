// Upsert (:GovernmentDecision)-[:CONCERNS]->(p:Party).
// Parameters: $government_decision_id, $party_id
MATCH (g:GovernmentDecision {government_decision_id: $government_decision_id})
MATCH (p:Party {party_id: $party_id})
MERGE (g)-[r:CONCERNS]->(p)
ON CREATE SET r.created_at = datetime(), r.target_label = 'Party'
ON MATCH SET r.updated_at = datetime()
RETURN g.government_decision_id AS government_decision_id, p.party_id AS target_id;
