// Upsert an Office node keyed by office_id.
// Parameters: $office_id (required), $canonical_name, $hebrew_name,
//             $english_name, $office_type
//             (e.g. 'mk','minister','deputy_minister'), $scope.
MERGE (o:Office {office_id: $office_id})
ON CREATE SET
  o.created_at = datetime(),
  o.canonical_name = $canonical_name,
  o.hebrew_name = coalesce($hebrew_name, $canonical_name, ''),
  o.english_name = coalesce($english_name, ''),
  o.office_type = $office_type,
  o.scope = $scope
ON MATCH SET
  o.updated_at = datetime(),
  o.canonical_name = coalesce($canonical_name, o.canonical_name),
  o.hebrew_name = coalesce($hebrew_name, o.hebrew_name, ''),
  o.english_name = coalesce($english_name, o.english_name, ''),
  o.office_type = coalesce($office_type, o.office_type),
  o.scope = coalesce($scope, o.scope)
RETURN o.office_id AS office_id;
