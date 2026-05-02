// Upsert (:Person)-[:HAS_POSITION_TERM]->(:PositionTerm).
// Parameters: $person_id, $position_term_id.
MATCH (p:Person {person_id: $person_id})
MATCH (pt:PositionTerm {position_term_id: $position_term_id})
MERGE (p)-[r:HAS_POSITION_TERM]->(pt)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN p.person_id AS person_id, pt.position_term_id AS position_term_id;
