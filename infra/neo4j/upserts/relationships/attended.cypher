// Upsert (:Person)-[:ATTENDED {presence}]->(:AttendanceEvent).
// Parameters:
//   $person_id — canonical person UUID (required)
//   $attendance_event_id — session UUID (required)
//   $presence — one of {'present','absent','partial'} (required)
// Modeled as a directed Person → AttendanceEvent edge so the vote
// retrieval graph query can walk from a person to every session they
// attended in a given time scope without joining through the session
// node payload.
MATCH (p:Person {person_id: $person_id})
MATCH (a:AttendanceEvent {attendance_event_id: $attendance_event_id})
WITH p, a, $presence AS presence
WHERE presence IS NOT NULL AND presence IN ['present', 'absent', 'partial']
MERGE (p)-[r:ATTENDED]->(a)
ON CREATE SET
  r.created_at = datetime(),
  r.presence = presence
ON MATCH SET
  r.updated_at = datetime(),
  r.presence = presence
RETURN p.person_id AS person_id, a.attendance_event_id AS attendance_event_id, r.presence AS presence;
