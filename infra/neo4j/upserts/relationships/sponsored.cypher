// Upsert (:Person)-[:SPONSORED]->(:Bill).
// No relationship properties; template is a plain idempotent MERGE.
// Parameters: $person_id, $bill_id.
MATCH (p:Person {person_id: $person_id})
MATCH (b:Bill {bill_id: $bill_id})
MERGE (p)-[r:SPONSORED]->(b)
ON CREATE SET r.created_at = datetime()
ON MATCH SET r.updated_at = datetime()
RETURN p.person_id AS person_id, b.bill_id AS bill_id;
