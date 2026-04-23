// Upsert a Committee node keyed by committee_id.
// Parameters: $committee_id (required), $canonical_name, $hebrew_name.
MERGE (c:Committee {committee_id: $committee_id})
ON CREATE SET
  c.created_at = datetime(),
  c.canonical_name = $canonical_name,
  c.hebrew_name = $hebrew_name
ON MATCH SET
  c.updated_at = datetime(),
  c.canonical_name = coalesce($canonical_name, c.canonical_name),
  c.hebrew_name = coalesce($hebrew_name, c.hebrew_name)
RETURN c.committee_id AS committee_id;
