// Graph retrieval for claim_type = statement_about_formal_action.
// Falls through to any evidence span that names the speaker AND mentions
// the optional bill/committee/office slot. This is a *weak* signal — the
// lexical + vector retrieval layer (W2-B2) is the primary source for this
// claim type; graph retrieval is used for cross-source consistency only.
MATCH (p:Person {person_id: $speaker_person_id})
OPTIONAL MATCH (p)<-[:ABOUT_PERSON]-(span:EvidenceSpan)
WITH p, collect(DISTINCT span.span_id) AS span_ids
RETURN
  {speaker_person_id: p.person_id} AS node_ids,
  {canonical_name: p.canonical_name,
   hebrew_name: p.hebrew_name,
   mention_count: size(span_ids)} AS properties,
  span_ids AS source_document_ids,
  2 AS source_tier
LIMIT 1;
