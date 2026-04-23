// Upsert an EvidenceSpan node keyed by span_id.
// Parameters: $span_id (required), $document_id, $source_tier (1|2|3),
//             $source_type, $url, $archive_uri, $text, $char_start,
//             $char_end, $captured_at (ISO-8601 datetime string).
MERGE (e:EvidenceSpan {span_id: $span_id})
ON CREATE SET
  e.created_at = datetime(),
  e.document_id = $document_id,
  e.source_tier = $source_tier,
  e.source_type = $source_type,
  e.url = $url,
  e.archive_uri = $archive_uri,
  e.text = $text,
  e.char_start = $char_start,
  e.char_end = $char_end,
  e.captured_at = CASE WHEN $captured_at IS NULL THEN null ELSE datetime($captured_at) END
ON MATCH SET
  e.updated_at = datetime(),
  e.document_id = coalesce($document_id, e.document_id),
  e.source_tier = coalesce($source_tier, e.source_tier),
  e.source_type = coalesce($source_type, e.source_type),
  e.url = coalesce($url, e.url),
  e.archive_uri = coalesce($archive_uri, e.archive_uri),
  e.text = coalesce($text, e.text),
  e.char_start = coalesce($char_start, e.char_start),
  e.char_end = coalesce($char_end, e.char_end),
  e.captured_at = CASE WHEN $captured_at IS NULL THEN e.captured_at ELSE datetime($captured_at) END
RETURN e.span_id AS span_id;
