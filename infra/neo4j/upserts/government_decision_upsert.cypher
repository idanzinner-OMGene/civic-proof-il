// Upsert a GovernmentDecision node keyed by government_decision_id.
// Parameters: $government_decision_id (required), $decision_number (nullable),
//             $government_number (nullable integer), $decision_date (ISO-8601, nullable),
//             $title, $summary (nullable), $issuing_body (nullable),
//             $source_document_id (nullable).
MERGE (g:GovernmentDecision {government_decision_id: $government_decision_id})
ON CREATE SET
  g.created_at = datetime(),
  g.decision_number = $decision_number,
  g.government_number = $government_number,
  g.decision_date = CASE WHEN $decision_date IS NULL THEN null ELSE datetime($decision_date) END,
  g.title = $title,
  g.summary = $summary,
  g.issuing_body = $issuing_body,
  g.source_document_id = $source_document_id
ON MATCH SET
  g.updated_at = datetime(),
  g.decision_number = coalesce($decision_number, g.decision_number),
  g.government_number = coalesce($government_number, g.government_number),
  g.decision_date = CASE WHEN $decision_date IS NULL THEN g.decision_date ELSE datetime($decision_date) END,
  g.title = coalesce($title, g.title),
  g.summary = coalesce($summary, g.summary),
  g.issuing_body = coalesce($issuing_body, g.issuing_body),
  g.source_document_id = coalesce($source_document_id, g.source_document_id)
RETURN g.government_decision_id AS government_decision_id;
