// Upsert a Person node keyed by person_id.
// Parameters: $person_id (required), $canonical_name, $hebrew_name,
//             $english_name, $external_ids (JSON string of a map), $source_tier.
// Null params are ignored on update (coalesce keeps existing values).
MERGE (p:Person {person_id: $person_id})
ON CREATE SET
  p.created_at = datetime(),
  p.canonical_name = $canonical_name,
  p.hebrew_name = $hebrew_name,
  p.english_name = $english_name,
  p.external_ids = $external_ids,
  p.source_tier = $source_tier
ON MATCH SET
  p.updated_at = datetime(),
  p.canonical_name = coalesce($canonical_name, p.canonical_name),
  p.hebrew_name = coalesce($hebrew_name, p.hebrew_name),
  p.english_name = coalesce($english_name, p.english_name),
  p.external_ids = coalesce($external_ids, p.external_ids),
  p.source_tier = coalesce($source_tier, p.source_tier)
RETURN p.person_id AS person_id;
