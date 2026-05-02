// Upsert (:Declaration)-[:SAID_BY]->(:Person).
// Parameters: $declaration_id, $person_id.
MATCH (d:Declaration {declaration_id: $declaration_id})
MATCH (p:Person {person_id: $person_id})
MERGE (d)-[r:SAID_BY]->(p)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN d.declaration_id AS declaration_id, p.person_id AS person_id;
