// Graph retrieval for claim_type = committee_attendance.
// Parameters: $speaker_person_id, $committee_id, $time_start, $time_end.
MATCH (p:Person {person_id: $speaker_person_id})-[att:ATTENDED]->(a:AttendanceEvent)
MATCH (a)-[:ABOUT_PERSON|:MEMBER_OF_COMMITTEE|:HAS_SPAN]->()
MATCH (c:Committee {committee_id: $committee_id})
WHERE a.committee_id = c.committee_id
  AND ($time_start IS NULL OR a.occurred_at >= datetime($time_start))
  AND ($time_end IS NULL OR a.occurred_at <= datetime($time_end))
RETURN
  {speaker_person_id: p.person_id,
   committee_id: c.committee_id,
   attendance_event_id: a.attendance_event_id} AS node_ids,
  {presence: att.presence,
   occurred_at: toString(a.occurred_at)} AS properties,
  [] AS source_document_ids,
  1 AS source_tier
ORDER BY a.occurred_at DESC
LIMIT 20;
