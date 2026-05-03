// Graph retrieval for claim_type = election_result.
// Parameters: $party_id (required UUID string),
//             $time_start (ISO string, optional), $time_end (ISO, optional).
MATCH (e:ElectionResult)-[:FOR_PARTY]->(p:Party {party_id: $party_id})
WHERE ($time_start IS NULL OR e.election_date >= datetime($time_start))
  AND ($time_end IS NULL OR e.election_date <= datetime($time_end))
RETURN
  {party_id: p.party_id, election_result_id: e.election_result_id} AS node_ids,
  {list_name: e.list_name, ballot_letters: e.ballot_letters,
   knesset_number: e.knesset_number, election_date: toString(e.election_date),
   votes: e.votes, seats_won: e.seats_won,
   vote_share: e.vote_share, passed_threshold: e.passed_threshold} AS properties,
  CASE WHEN e.source_document_id IS NOT NULL
       THEN [e.source_document_id] ELSE [] END AS source_document_ids,
  1 AS source_tier
ORDER BY e.knesset_number DESC
LIMIT 10;
