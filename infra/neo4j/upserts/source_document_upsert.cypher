// Upsert a SourceDocument node keyed by document_id.
// Parameters: $document_id (required), $source_family, $source_tier (1|2|3),
//             $source_type, $url, $archive_uri, $content_sha256,
//             $captured_at (ISO-8601 datetime string), $language, $title.
MERGE (s:SourceDocument {document_id: $document_id})
ON CREATE SET
  s.created_at = datetime(),
  s.source_family = $source_family,
  s.source_tier = $source_tier,
  s.source_type = $source_type,
  s.url = $url,
  s.archive_uri = $archive_uri,
  s.content_sha256 = $content_sha256,
  s.captured_at = CASE WHEN $captured_at IS NULL THEN null ELSE datetime($captured_at) END,
  s.language = $language,
  s.title = $title
ON MATCH SET
  s.updated_at = datetime(),
  s.source_family = coalesce($source_family, s.source_family),
  s.source_tier = coalesce($source_tier, s.source_tier),
  s.source_type = coalesce($source_type, s.source_type),
  s.url = coalesce($url, s.url),
  s.archive_uri = coalesce($archive_uri, s.archive_uri),
  s.content_sha256 = coalesce($content_sha256, s.content_sha256),
  s.captured_at = CASE WHEN $captured_at IS NULL THEN s.captured_at ELSE datetime($captured_at) END,
  s.language = coalesce($language, s.language),
  s.title = coalesce($title, s.title)
RETURN s.document_id AS document_id;
