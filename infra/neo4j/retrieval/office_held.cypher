// Graph retrieval for claim_type = office_held.
// Parameters: $speaker_person_id, $office_id, $time_start, $time_end.
//
// V2 primary path: uses PositionTerm nodes for richer metadata
// (appointing_body, is_acting, source provenance).  Falls back to the
// legacy HELD_OFFICE edge so graphs not yet re-ingested still work.
MATCH (p:Person {person_id: $speaker_person_id})
      -[:HAS_POSITION_TERM]->(pt:PositionTerm)
      -[:ABOUT_OFFICE]->(o:Office {office_id: $office_id})
WHERE ($time_start IS NULL OR pt.valid_to IS NULL OR pt.valid_to >= datetime($time_start))
  AND ($time_end IS NULL OR pt.valid_from <= datetime($time_end))
RETURN
  {speaker_person_id: p.person_id, office_id: o.office_id,
   position_term_id: pt.position_term_id} AS node_ids,
  {canonical_name: o.canonical_name,
   office_type: o.office_type,
   appointing_body: pt.appointing_body,
   valid_from: toString(pt.valid_from),
   valid_to: toString(pt.valid_to),
   is_acting: pt.is_acting} AS properties,
  CASE WHEN pt.source_document_id IS NOT NULL
       THEN [pt.source_document_id] ELSE [] END AS source_document_ids,
  1 AS source_tier
UNION
// Legacy fallback: HELD_OFFICE edge (v1 graph, pre-ingest or non-ministerial).
MATCH (p:Person {person_id: $speaker_person_id})-[r:HELD_OFFICE]->(o:Office {office_id: $office_id})
WHERE ($time_start IS NULL OR r.valid_to IS NULL OR r.valid_to >= datetime($time_start))
  AND ($time_end IS NULL OR r.valid_from <= datetime($time_end))
  AND NOT (p)-[:HAS_POSITION_TERM]->(:PositionTerm)-[:ABOUT_OFFICE]->(o)
RETURN
  {speaker_person_id: p.person_id, office_id: o.office_id} AS node_ids,
  {canonical_name: o.canonical_name,
   office_type: o.office_type,
   valid_from: toString(r.valid_from),
   valid_to: toString(r.valid_to)} AS properties,
  [] AS source_document_ids,
  1 AS source_tier
LIMIT 10;
