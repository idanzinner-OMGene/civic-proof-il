// Upsert (:GovernmentDecision)-[:CONCERNS]->(o:Office).
// Parameters: $government_decision_id, $office_id
MATCH (g:GovernmentDecision {government_decision_id: $government_decision_id})
MATCH (o:Office {office_id: $office_id})
MERGE (g)-[r:CONCERNS]->(o)
ON CREATE SET r.created_at = datetime(), r.target_label = 'Office'
ON MATCH SET r.updated_at = datetime()
RETURN g.government_decision_id AS government_decision_id, o.office_id AS target_id;
