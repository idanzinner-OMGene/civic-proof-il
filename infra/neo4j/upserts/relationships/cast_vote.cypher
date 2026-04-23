// Upsert (:Person)-[:CAST_VOTE {value}]->(:VoteEvent).
// Parameters: $person_id, $vote_event_id,
//             $value ∈ {'for','against','abstain'} (required — enforced here
//             since Neo4j Community can't declare relationship-property
//             existence constraints).
MATCH (p:Person {person_id: $person_id})
MATCH (v:VoteEvent {vote_event_id: $vote_event_id})
WITH p, v, $value AS value
WHERE value IS NOT NULL AND value IN ['for', 'against', 'abstain']
MERGE (p)-[r:CAST_VOTE]->(v)
ON CREATE SET
  r.created_at = datetime(),
  r.value = value
ON MATCH SET
  r.updated_at = datetime(),
  r.value = value
RETURN p.person_id AS person_id, v.vote_event_id AS vote_event_id, r.value AS value;
