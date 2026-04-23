// Upsert (:Person)-[:HELD_OFFICE {valid_from, valid_to}]->(:Office).
// Parameters: $person_id, $office_id, $valid_from (ISO-8601, required),
//             $valid_to (ISO-8601, nullable = open-ended).
MATCH (p:Person {person_id: $person_id})
MATCH (o:Office {office_id: $office_id})
WITH p, o, $valid_from AS valid_from, $valid_to AS valid_to
WHERE valid_from IS NOT NULL
MERGE (p)-[r:HELD_OFFICE]->(o)
ON CREATE SET
  r.created_at = datetime(),
  r.valid_from = datetime(valid_from),
  r.valid_to = CASE WHEN valid_to IS NULL THEN null ELSE datetime(valid_to) END
ON MATCH SET
  r.updated_at = datetime(),
  r.valid_from = datetime(valid_from),
  r.valid_to = CASE WHEN valid_to IS NULL THEN r.valid_to ELSE datetime(valid_to) END
RETURN p.person_id AS person_id, o.office_id AS office_id;
