// Upsert (:GovernmentDecision)-[:CONCERNS]->(c:Committee).
// Parameters: $government_decision_id, $committee_id
MATCH (g:GovernmentDecision {government_decision_id: $government_decision_id})
MATCH (c:Committee {committee_id: $committee_id})
MERGE (g)-[r:CONCERNS]->(c)
ON CREATE SET r.created_at = datetime(), r.target_label = 'Committee'
ON MATCH SET r.updated_at = datetime()
RETURN g.government_decision_id AS government_decision_id, c.committee_id AS target_id;
