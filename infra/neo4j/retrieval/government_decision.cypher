// Graph retrieval for claim_type = government_decision.
// Parameters: $government_decision_id (optional UUID string — direct lookup),
//             $decision_number         (optional string — e.g. "2084"),
//             $government_number       (optional integer),
//             $time_start              (ISO string, optional),
//             $time_end                (ISO string, optional).
//
// When $government_decision_id is provided the query does a direct lookup
// (fastest path). Otherwise it falls back to $decision_number + optional
// $government_number. At least one of the two must be set for the retriever
// to return rows; the checkability classifier rejects the claim otherwise.
MATCH (d:GovernmentDecision)
WHERE (
    ($government_decision_id IS NOT NULL AND d.government_decision_id = $government_decision_id)
    OR
    ($government_decision_id IS NULL AND $decision_number IS NOT NULL
     AND d.decision_number = $decision_number
     AND ($government_number IS NULL OR d.government_number = $government_number))
)
AND ($time_start IS NULL OR d.decision_date >= datetime($time_start))
AND ($time_end   IS NULL OR d.decision_date <= datetime($time_end))
RETURN
  {government_decision_id: d.government_decision_id} AS node_ids,
  {decision_number: d.decision_number,
   government_number: d.government_number,
   decision_date: toString(d.decision_date),
   title: d.title,
   summary: d.summary,
   issuing_body: d.issuing_body} AS properties,
  CASE WHEN d.source_document_id IS NOT NULL
       THEN [d.source_document_id] ELSE [] END AS source_document_ids,
  1 AS source_tier
ORDER BY d.decision_date DESC
LIMIT 5;
