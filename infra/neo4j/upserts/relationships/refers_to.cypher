// Upsert (:Declaration)-[:REFERS_TO]->(target).
// The target may be a VoteEvent, Bill, PositionTerm, GovernmentDecision, or
// ElectionResult. The caller passes $target_label to select the right MATCH.
//
// Parameters: $declaration_id, $target_id, $target_label
//   (one of: 'VoteEvent', 'Bill', 'PositionTerm', 'GovernmentDecision', 'ElectionResult').
//
// NOTE: Neo4j Community does not support dynamic labels in a single template.
// Call the appropriate label-specific variant or use CALL apoc.do.when if APOC
// is available. This template handles VoteEvent as the default; extend as needed.
MATCH (d:Declaration {declaration_id: $declaration_id})
MATCH (t {vote_event_id: $target_id})
WHERE $target_label = 'VoteEvent'
MERGE (d)-[r:REFERS_TO]->(t)
ON CREATE SET r.created_at = datetime(), r.target_label = $target_label
ON MATCH SET r.updated_at = datetime()
RETURN d.declaration_id AS declaration_id, $target_id AS target_id;
