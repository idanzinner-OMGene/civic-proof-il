// Upsert (:SourceDocument)-[:HAS_SPAN]->(:EvidenceSpan).
// No relationship properties; template is a plain idempotent MERGE.
// Parameters: $document_id, $span_id.
MATCH (s:SourceDocument {document_id: $document_id})
MATCH (e:EvidenceSpan {span_id: $span_id})
MERGE (s)-[r:HAS_SPAN]->(e)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN s.document_id AS document_id, e.span_id AS span_id;
