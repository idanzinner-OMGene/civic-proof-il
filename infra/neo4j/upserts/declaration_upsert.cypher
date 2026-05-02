// Upsert a Declaration node keyed by declaration_id.
// Parameters: $declaration_id (required), $speaker_person_id (nullable),
//             $utterance_text, $utterance_language,
//             $utterance_time (ISO-8601 datetime string, nullable),
//             $source_document_id, $source_kind, $quoted_span (nullable),
//             $canonicalized_text (nullable), $claim_family, $checkability,
//             $derived_atomic_claim_ids (list of strings).
MERGE (d:Declaration {declaration_id: $declaration_id})
ON CREATE SET
  d.created_at = datetime(),
  d.speaker_person_id = $speaker_person_id,
  d.utterance_text = $utterance_text,
  d.utterance_language = $utterance_language,
  d.utterance_time = CASE WHEN $utterance_time IS NULL THEN null ELSE datetime($utterance_time) END,
  d.source_document_id = $source_document_id,
  d.source_kind = $source_kind,
  d.quoted_span = $quoted_span,
  d.canonicalized_text = $canonicalized_text,
  d.claim_family = $claim_family,
  d.checkability = $checkability,
  d.derived_atomic_claim_ids = $derived_atomic_claim_ids
ON MATCH SET
  d.updated_at = datetime(),
  d.speaker_person_id = coalesce($speaker_person_id, d.speaker_person_id),
  d.utterance_text = coalesce($utterance_text, d.utterance_text),
  d.utterance_language = coalesce($utterance_language, d.utterance_language),
  d.utterance_time = CASE WHEN $utterance_time IS NULL THEN d.utterance_time ELSE datetime($utterance_time) END,
  d.source_document_id = coalesce($source_document_id, d.source_document_id),
  d.source_kind = coalesce($source_kind, d.source_kind),
  d.quoted_span = coalesce($quoted_span, d.quoted_span),
  d.canonicalized_text = coalesce($canonicalized_text, d.canonicalized_text),
  d.claim_family = coalesce($claim_family, d.claim_family),
  d.checkability = coalesce($checkability, d.checkability),
  d.derived_atomic_claim_ids = coalesce($derived_atomic_claim_ids, d.derived_atomic_claim_ids)
RETURN d.declaration_id AS declaration_id;
