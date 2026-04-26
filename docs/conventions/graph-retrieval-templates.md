# Convention: Graph retrieval templates

Location: `infra/neo4j/retrieval/<claim_type>.cypher`, one file per
supported `claim_type`. The set is pinned by
`tests/smoke/test_alignment.py::test_retrieval_templates_exactly_six`.

## Contract

* Templates are parameterised Cypher queries loaded by
  `civic_retrieval.graph.GraphRetriever`.
* Parameters come from the resolved claim's slot dict: e.g.
  `$speaker_person_id`, `$bill_id`, `$committee_id`, `$office_id`.
* Templates return a row shape that the retriever can project onto
  `GraphEvidence(claim_type, node_ids, properties,
  source_document_ids, source_tier)`. The minimum RETURN columns are:
  * `claim_type` — the template's own claim type (string literal)
  * `node_ids` — a map of slot → UUID
  * `properties` — a map of evidence-relevant properties
    (`vote_value`, `occurred_at`, `presence`, `valid_from`,
    `valid_to`, …)
  * `source_document_ids` — a list of `:SourceDocument.document_id`
    UUIDs that corroborate the fact
  * `source_tier` — the Tier assigned by the source document (1, 2,
    or 3)

## Adding a claim_type

1. Add `<claim_type>.cypher` under `infra/neo4j/retrieval/`.
2. Add a row to `SUPPORTED_CLAIM_TYPES` in
   `tests/smoke/test_alignment.py` (already does the assert).
3. Update `civic_verification.engine._compare` with the new claim
   type's verdict logic.
4. Run `uv run --package civic-retrieval pytest
   services/retrieval/tests/ -q` to make sure the dispatch picks up
   the new file.

## Don't

* Don't write a template that returns empty `source_document_ids` —
  the verdict engine requires at least one source document per fact
  for the provenance bundler to render.
* Don't MERGE / CREATE / SET / DELETE in a retrieval template.
  Retrieval is READ-ONLY; writes happen in the adapter upsert
  templates under `infra/neo4j/upserts/`.
* Don't rely on Neo4j's `CALL db.schema.visualization` or other
  introspection calls inside a template — production Neo4j may be
  Enterprise with RBAC locking these down.
