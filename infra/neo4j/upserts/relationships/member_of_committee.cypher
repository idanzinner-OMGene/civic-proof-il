// Upsert (:Person)-[:MEMBER_OF_COMMITTEE {valid_from, valid_to}]->(:Committee).
// Parameters: $person_id, $committee_id, $valid_from (ISO-8601, required),
//             $valid_to (ISO-8601, nullable = open-ended).
MATCH (p:Person {person_id: $person_id})
MATCH (c:Committee {committee_id: $committee_id})
WITH p, c, $valid_from AS valid_from, $valid_to AS valid_to
WHERE valid_from IS NOT NULL
MERGE (p)-[r:MEMBER_OF_COMMITTEE]->(c)
ON CREATE SET
  r.created_at = datetime(),
  r.valid_from = datetime(valid_from),
  r.valid_to = CASE WHEN valid_to IS NULL THEN null ELSE datetime(valid_to) END
ON MATCH SET
  r.updated_at = datetime(),
  r.valid_from = datetime(valid_from),
  r.valid_to = CASE WHEN valid_to IS NULL THEN r.valid_to ELSE datetime(valid_to) END
RETURN p.person_id AS person_id, c.committee_id AS committee_id;
