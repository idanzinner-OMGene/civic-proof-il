// Upsert an ElectionResult node keyed by election_result_id.
// Parameters: $election_result_id (required), $election_date (ISO-8601, nullable),
//             $list_party_id (nullable), $votes (nullable integer),
//             $seats_won (nullable integer), $vote_share (nullable float),
//             $passed_threshold (nullable boolean), $source_document_id (nullable).
MERGE (e:ElectionResult {election_result_id: $election_result_id})
ON CREATE SET
  e.created_at = datetime(),
  e.election_date = CASE WHEN $election_date IS NULL THEN null ELSE datetime($election_date) END,
  e.list_party_id = $list_party_id,
  e.votes = $votes,
  e.seats_won = $seats_won,
  e.vote_share = $vote_share,
  e.passed_threshold = $passed_threshold,
  e.source_document_id = $source_document_id
ON MATCH SET
  e.updated_at = datetime(),
  e.election_date = CASE WHEN $election_date IS NULL THEN e.election_date ELSE datetime($election_date) END,
  e.list_party_id = coalesce($list_party_id, e.list_party_id),
  e.votes = coalesce($votes, e.votes),
  e.seats_won = coalesce($seats_won, e.seats_won),
  e.vote_share = coalesce($vote_share, e.vote_share),
  e.passed_threshold = coalesce($passed_threshold, e.passed_threshold),
  e.source_document_id = coalesce($source_document_id, e.source_document_id)
RETURN e.election_result_id AS election_result_id;
