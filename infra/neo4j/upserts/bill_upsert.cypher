// Upsert a Bill node keyed by bill_id.
// Parameters: $bill_id (required), $title, $hebrew_name, $english_name,
//             $knesset_number, $status.
MERGE (b:Bill {bill_id: $bill_id})
ON CREATE SET
  b.created_at = datetime(),
  b.title = $title,
  b.hebrew_name = coalesce($hebrew_name, $title, ''),
  b.english_name = coalesce($english_name, ''),
  b.knesset_number = $knesset_number,
  b.status = $status
ON MATCH SET
  b.updated_at = datetime(),
  b.title = coalesce($title, b.title),
  b.hebrew_name = coalesce($hebrew_name, b.hebrew_name, ''),
  b.english_name = coalesce($english_name, b.english_name, ''),
  b.knesset_number = coalesce($knesset_number, b.knesset_number),
  b.status = coalesce($status, b.status)
RETURN b.bill_id AS bill_id;
