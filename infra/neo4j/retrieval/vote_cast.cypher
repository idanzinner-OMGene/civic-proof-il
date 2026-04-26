// Graph retrieval for claim_type = vote_cast.
// Parameters: $speaker_person_id (required), $bill_id (required),
//             $time_start (ISO string, optional), $time_end (ISO, optional).
// Returns: the CAST_VOTE relationship value(s) cast by the speaker on any
// VoteEvent whose underlying bill matches $bill_id and whose occurred_at
// falls inside [$time_start, $time_end]. Also pulls the source document IDs
// from the VoteEvent's HAS_SPAN / SourceDocument chain for provenance.
MATCH (p:Person {person_id: $speaker_person_id})-[r:CAST_VOTE]->(v:VoteEvent)
MATCH (v)-[:ABOUT_BILL]->(b:Bill {bill_id: $bill_id})
WHERE ($time_start IS NULL OR v.occurred_at >= datetime($time_start))
  AND ($time_end IS NULL OR v.occurred_at <= datetime($time_end))
OPTIONAL MATCH (v)-[:HAS_SPAN]->(s:EvidenceSpan)-[:HAS_SPAN]-(d:SourceDocument)
WITH p, v, b, r,
     collect(DISTINCT d.document_id) AS doc_ids
RETURN
  {speaker_person_id: p.person_id,
   vote_event_id: v.vote_event_id,
   bill_id: b.bill_id} AS node_ids,
  {vote_value: r.value,
   occurred_at: toString(v.occurred_at),
   bill_title: b.title} AS properties,
  doc_ids AS source_document_ids,
  1 AS source_tier
ORDER BY v.occurred_at DESC
LIMIT 10;
