// Upsert (:Declaration)-[:REFERS_TO]->(g:GovernmentDecision).
// Parameters: $declaration_id, $government_decision_id
MATCH (d:Declaration {declaration_id: $declaration_id})
MATCH (g:GovernmentDecision {government_decision_id: $government_decision_id})
MERGE (d)-[r:REFERS_TO]->(g)
ON CREATE SET r.created_at = datetime(), r.target_label = 'GovernmentDecision'
ON MATCH SET r.updated_at = datetime()
RETURN d.declaration_id AS declaration_id, g.government_decision_id AS target_id;
