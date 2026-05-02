// Upsert (:Declaration)-[:FROM_SOURCE]->(:SourceDocument).
// Parameters: $declaration_id, $document_id.
MATCH (d:Declaration {declaration_id: $declaration_id})
MATCH (s:SourceDocument {document_id: $document_id})
MERGE (d)-[r:FROM_SOURCE]->(s)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN d.declaration_id AS declaration_id, s.document_id AS document_id;
