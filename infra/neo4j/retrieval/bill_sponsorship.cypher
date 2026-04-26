// Graph retrieval for claim_type = bill_sponsorship.
// Parameters: $speaker_person_id (required), $bill_id (required).
MATCH (p:Person {person_id: $speaker_person_id})-[r:SPONSORED]->(b:Bill {bill_id: $bill_id})
OPTIONAL MATCH (b)-[:HAS_SPAN]->(s:EvidenceSpan)-[:HAS_SPAN]-(d:SourceDocument)
WITH p, b, r, collect(DISTINCT d.document_id) AS doc_ids
RETURN
  {speaker_person_id: p.person_id, bill_id: b.bill_id} AS node_ids,
  {bill_title: b.title, sponsored_at: toString(r.created_at),
   knesset_number: b.knesset_number} AS properties,
  doc_ids AS source_document_ids,
  1 AS source_tier
LIMIT 10;
