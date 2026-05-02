// Upsert (:ElectionResult)-[:FOR_PARTY]->(:Party).
// Parameters: $election_result_id, $party_id.
MATCH (e:ElectionResult {election_result_id: $election_result_id})
MATCH (p:Party {party_id: $party_id})
MERGE (e)-[r:FOR_PARTY]->(p)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN e.election_result_id AS election_result_id, p.party_id AS party_id;
