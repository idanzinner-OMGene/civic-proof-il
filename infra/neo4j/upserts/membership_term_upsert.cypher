// Upsert a MembershipTerm node keyed by membership_term_id.
// Parameters: $membership_term_id (required), $person_id, $org_id,
//             $org_type (e.g. 'party','committee','office'),
//             $valid_from (ISO-8601 datetime string),
//             $valid_to (ISO-8601 datetime string, nullable = open-ended).
MERGE (m:MembershipTerm {membership_term_id: $membership_term_id})
ON CREATE SET
  m.created_at = datetime(),
  m.person_id = $person_id,
  m.org_id = $org_id,
  m.org_type = $org_type,
  m.valid_from = CASE WHEN $valid_from IS NULL THEN null ELSE datetime($valid_from) END,
  m.valid_to = CASE WHEN $valid_to IS NULL THEN null ELSE datetime($valid_to) END
ON MATCH SET
  m.updated_at = datetime(),
  m.person_id = coalesce($person_id, m.person_id),
  m.org_id = coalesce($org_id, m.org_id),
  m.org_type = coalesce($org_type, m.org_type),
  m.valid_from = CASE WHEN $valid_from IS NULL THEN m.valid_from ELSE datetime($valid_from) END,
  m.valid_to = CASE WHEN $valid_to IS NULL THEN m.valid_to ELSE datetime($valid_to) END
RETURN m.membership_term_id AS membership_term_id;
