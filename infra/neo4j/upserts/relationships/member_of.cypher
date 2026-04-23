// Upsert (:Person)-[:MEMBER_OF {valid_from, valid_to}]->(:Party).
// Parameters: $person_id, $party_id, $valid_from (ISO-8601, required by
//             convention — enforced here since Neo4j Community can't declare
//             relationship-property existence constraints),
//             $valid_to (ISO-8601, nullable = open-ended).
//
// NOTE: $valid_from must not be null; we assert it explicitly so the template
// refuses to MERGE an invalid relationship.
MATCH (p:Person {person_id: $person_id})
MATCH (party:Party {party_id: $party_id})
WITH p, party, $valid_from AS valid_from, $valid_to AS valid_to
WHERE valid_from IS NOT NULL
MERGE (p)-[r:MEMBER_OF]->(party)
ON CREATE SET
  r.created_at = datetime(),
  r.valid_from = datetime(valid_from),
  r.valid_to = CASE WHEN valid_to IS NULL THEN null ELSE datetime(valid_to) END
ON MATCH SET
  r.updated_at = datetime(),
  r.valid_from = datetime(valid_from),
  r.valid_to = CASE WHEN valid_to IS NULL THEN r.valid_to ELSE datetime(valid_to) END
RETURN p.person_id AS person_id, party.party_id AS party_id;
