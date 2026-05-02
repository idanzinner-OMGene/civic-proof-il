// Upsert (:GovernmentDecision)-[:CONCERNS]->(target).
// Target may be a Person, Office, Committee, or Party.
// Parameters: $government_decision_id, $target_id, $target_label
//   (one of: 'Person', 'Office', 'Committee', 'Party').
//
// NOTE: Neo4j Community does not support dynamic labels in a single template.
// This template handles Person as the default; extend as needed or use APOC.
MATCH (g:GovernmentDecision {government_decision_id: $government_decision_id})
MATCH (t:Person {person_id: $target_id})
WHERE $target_label = 'Person'
MERGE (g)-[r:CONCERNS]->(t)
ON CREATE SET r.created_at = datetime(), r.target_label = $target_label
ON MATCH SET r.updated_at = datetime()
RETURN g.government_decision_id AS government_decision_id, $target_id AS target_id;
