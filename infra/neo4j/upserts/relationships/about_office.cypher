// Upsert (:PositionTerm)-[:ABOUT_OFFICE]->(:Office).
// Parameters: $position_term_id, $office_id.
MATCH (pt:PositionTerm {position_term_id: $position_term_id})
MATCH (o:Office {office_id: $office_id})
MERGE (pt)-[r:ABOUT_OFFICE]->(o)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN pt.position_term_id AS position_term_id, o.office_id AS office_id;
