// Upsert a Verdict node keyed by verdict_id.
// Parameters: $verdict_id (required), $claim_id, $status, $confidence_overall,
//             $confidence_source_authority, $confidence_directness,
//             $confidence_temporal_alignment, $confidence_entity_resolution,
//             $confidence_cross_source_consistency, $summary,
//             $needs_human_review (bool), $model_version, $ruleset_version,
//             $created_at (ISO-8601; falls back to datetime()).
MERGE (v:Verdict {verdict_id: $verdict_id})
ON CREATE SET
  v.created_at = CASE WHEN $created_at IS NULL THEN datetime() ELSE datetime($created_at) END,
  v.claim_id = $claim_id,
  v.status = $status,
  v.confidence_overall = $confidence_overall,
  v.confidence_source_authority = $confidence_source_authority,
  v.confidence_directness = $confidence_directness,
  v.confidence_temporal_alignment = $confidence_temporal_alignment,
  v.confidence_entity_resolution = $confidence_entity_resolution,
  v.confidence_cross_source_consistency = $confidence_cross_source_consistency,
  v.summary = $summary,
  v.needs_human_review = $needs_human_review,
  v.model_version = $model_version,
  v.ruleset_version = $ruleset_version
ON MATCH SET
  v.updated_at = datetime(),
  v.claim_id = coalesce($claim_id, v.claim_id),
  v.status = coalesce($status, v.status),
  v.confidence_overall = coalesce($confidence_overall, v.confidence_overall),
  v.confidence_source_authority = coalesce($confidence_source_authority, v.confidence_source_authority),
  v.confidence_directness = coalesce($confidence_directness, v.confidence_directness),
  v.confidence_temporal_alignment = coalesce($confidence_temporal_alignment, v.confidence_temporal_alignment),
  v.confidence_entity_resolution = coalesce($confidence_entity_resolution, v.confidence_entity_resolution),
  v.confidence_cross_source_consistency = coalesce($confidence_cross_source_consistency, v.confidence_cross_source_consistency),
  v.summary = coalesce($summary, v.summary),
  v.needs_human_review = coalesce($needs_human_review, v.needs_human_review),
  v.model_version = coalesce($model_version, v.model_version),
  v.ruleset_version = coalesce($ruleset_version, v.ruleset_version)
RETURN v.verdict_id AS verdict_id;
