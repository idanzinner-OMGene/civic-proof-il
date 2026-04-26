// Graph retrieval for claim_type = office_held.
// Parameters: $speaker_person_id, $office_id, $time_start, $time_end.
MATCH (p:Person {person_id: $speaker_person_id})-[r:HELD_OFFICE]->(o:Office {office_id: $office_id})
WHERE ($time_start IS NULL OR r.valid_to IS NULL OR r.valid_to >= datetime($time_start))
  AND ($time_end IS NULL OR r.valid_from <= datetime($time_end))
RETURN
  {speaker_person_id: p.person_id, office_id: o.office_id} AS node_ids,
  {canonical_name: o.canonical_name,
   office_type: o.office_type,
   valid_from: toString(r.valid_from),
   valid_to: toString(r.valid_to)} AS properties,
  [] AS source_document_ids,
  1 AS source_tier
LIMIT 10;
