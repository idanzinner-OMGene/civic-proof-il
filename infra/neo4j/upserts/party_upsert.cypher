// Upsert a Party node keyed by party_id.
// Parameters: $party_id (required), $canonical_name, $hebrew_name,
//             $english_name, $abbreviation.
MERGE (p:Party {party_id: $party_id})
ON CREATE SET
  p.created_at = datetime(),
  p.canonical_name = $canonical_name,
  p.hebrew_name = $hebrew_name,
  p.english_name = coalesce($english_name, ''),
  p.abbreviation = $abbreviation
ON MATCH SET
  p.updated_at = datetime(),
  p.canonical_name = coalesce($canonical_name, p.canonical_name),
  p.hebrew_name = coalesce($hebrew_name, p.hebrew_name),
  p.english_name = coalesce($english_name, p.english_name, ''),
  p.abbreviation = coalesce($abbreviation, p.abbreviation)
RETURN p.party_id AS party_id;
