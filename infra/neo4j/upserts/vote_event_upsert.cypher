// Upsert a VoteEvent node keyed by vote_event_id.
// Parameters: $vote_event_id (required), $bill_id, $occurred_at (ISO-8601 datetime
//             string, converted via datetime()), $vote_type.
MERGE (v:VoteEvent {vote_event_id: $vote_event_id})
ON CREATE SET
  v.created_at = datetime(),
  v.bill_id = $bill_id,
  v.occurred_at = CASE WHEN $occurred_at IS NULL THEN null ELSE datetime($occurred_at) END,
  v.vote_type = $vote_type
ON MATCH SET
  v.updated_at = datetime(),
  v.bill_id = coalesce($bill_id, v.bill_id),
  v.occurred_at = CASE WHEN $occurred_at IS NULL THEN v.occurred_at ELSE datetime($occurred_at) END,
  v.vote_type = coalesce($vote_type, v.vote_type)
RETURN v.vote_event_id AS vote_event_id;
