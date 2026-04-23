// Upsert an AttendanceEvent node keyed by attendance_event_id.
// Parameters: $attendance_event_id (required), $committee_id,
//             $occurred_at (ISO-8601 datetime string).
MERGE (a:AttendanceEvent {attendance_event_id: $attendance_event_id})
ON CREATE SET
  a.created_at = datetime(),
  a.committee_id = $committee_id,
  a.occurred_at = CASE WHEN $occurred_at IS NULL THEN null ELSE datetime($occurred_at) END
ON MATCH SET
  a.updated_at = datetime(),
  a.committee_id = coalesce($committee_id, a.committee_id),
  a.occurred_at = CASE WHEN $occurred_at IS NULL THEN a.occurred_at ELSE datetime($occurred_at) END
RETURN a.attendance_event_id AS attendance_event_id;
