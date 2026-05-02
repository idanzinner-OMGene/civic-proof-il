// Upsert a PositionTerm node keyed by position_term_id.
// Parameters: $position_term_id (required), $person_id, $office_id,
//             $appointing_body (nullable), $valid_from (ISO-8601, nullable),
//             $valid_to (ISO-8601, nullable), $is_acting (boolean),
//             $source_document_id (nullable).
MERGE (p:PositionTerm {position_term_id: $position_term_id})
ON CREATE SET
  p.created_at = datetime(),
  p.person_id = $person_id,
  p.office_id = $office_id,
  p.appointing_body = $appointing_body,
  p.valid_from = CASE WHEN $valid_from IS NULL THEN null ELSE datetime($valid_from) END,
  p.valid_to = CASE WHEN $valid_to IS NULL THEN null ELSE datetime($valid_to) END,
  p.is_acting = $is_acting,
  p.source_document_id = $source_document_id
ON MATCH SET
  p.updated_at = datetime(),
  p.person_id = coalesce($person_id, p.person_id),
  p.office_id = coalesce($office_id, p.office_id),
  p.appointing_body = coalesce($appointing_body, p.appointing_body),
  p.valid_from = CASE WHEN $valid_from IS NULL THEN p.valid_from ELSE datetime($valid_from) END,
  p.valid_to = CASE WHEN $valid_to IS NULL THEN p.valid_to ELSE datetime($valid_to) END,
  p.is_acting = coalesce($is_acting, p.is_acting),
  p.source_document_id = coalesce($source_document_id, p.source_document_id)
RETURN p.position_term_id AS position_term_id;
