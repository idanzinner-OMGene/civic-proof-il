// Upsert an AtomicClaim node keyed by claim_id.
// Parameters: $claim_id (required), $raw_text, $normalized_text, $claim_type,
//             $speaker_person_id, $target_person_id, $bill_id, $committee_id,
//             $office_id, $vote_value, $time_scope_start (ISO-8601),
//             $time_scope_end (ISO-8601), $time_scope_granularity,
//             $checkability, $created_at (ISO-8601; falls back to datetime()).
MERGE (c:AtomicClaim {claim_id: $claim_id})
ON CREATE SET
  c.created_at = CASE WHEN $created_at IS NULL THEN datetime() ELSE datetime($created_at) END,
  c.raw_text = $raw_text,
  c.normalized_text = $normalized_text,
  c.claim_type = $claim_type,
  c.speaker_person_id = $speaker_person_id,
  c.target_person_id = $target_person_id,
  c.bill_id = $bill_id,
  c.committee_id = $committee_id,
  c.office_id = $office_id,
  c.vote_value = $vote_value,
  c.time_scope_start = CASE WHEN $time_scope_start IS NULL THEN null ELSE datetime($time_scope_start) END,
  c.time_scope_end = CASE WHEN $time_scope_end IS NULL THEN null ELSE datetime($time_scope_end) END,
  c.time_scope_granularity = $time_scope_granularity,
  c.checkability = $checkability
ON MATCH SET
  c.updated_at = datetime(),
  c.raw_text = coalesce($raw_text, c.raw_text),
  c.normalized_text = coalesce($normalized_text, c.normalized_text),
  c.claim_type = coalesce($claim_type, c.claim_type),
  c.speaker_person_id = coalesce($speaker_person_id, c.speaker_person_id),
  c.target_person_id = coalesce($target_person_id, c.target_person_id),
  c.bill_id = coalesce($bill_id, c.bill_id),
  c.committee_id = coalesce($committee_id, c.committee_id),
  c.office_id = coalesce($office_id, c.office_id),
  c.vote_value = coalesce($vote_value, c.vote_value),
  c.time_scope_start = CASE WHEN $time_scope_start IS NULL THEN c.time_scope_start ELSE datetime($time_scope_start) END,
  c.time_scope_end = CASE WHEN $time_scope_end IS NULL THEN c.time_scope_end ELSE datetime($time_scope_end) END,
  c.time_scope_granularity = coalesce($time_scope_granularity, c.time_scope_granularity),
  c.checkability = coalesce($checkability, c.checkability)
RETURN c.claim_id AS claim_id;
