# civic-retrieval

Graph + lexical evidence retrieval plus a deterministic reranker for
the Phase-4 `/claims/verify` slice.

## Surface

```python
from civic_retrieval import (
    GraphEvidence, GraphRetriever, run_graph_retrieval,
    LexicalEvidence, LexicalRetriever, MockLexicalRetriever,
    Evidence, RerankScore, rerank,
)
```

## Layers

1. **Graph retrieval** (`graph.py`) — loads one Cypher template per
   `claim_type` from `infra/neo4j/retrieval/<claim_type>.cypher`,
   binds the resolved slots as parameters, and returns typed
   `GraphEvidence` records. See
   `docs/conventions/graph-retrieval-templates.md`.
2. **Lexical retrieval** (`lexical.py`) — BM25 + optional kNN over
   OpenSearch `evidence_spans`. The index template declares
   `normalized_text` (BM25) + `embedding` (knn_vector, 384-dim).
   `MockLexicalRetriever` is provided for hermetic tests.
3. **Reranker** (`rerank.py`) — combines five weighted signals:
   `source_tier` (0.30), `directness` (0.25), `temporal_alignment`
   (0.20), `entity_resolution` (0.15), `cross_source_consistency`
   (0.10). `WEIGHTS` is the single source of truth — the
   verification rubric imports it.

## Invariants

- Retrieval templates are READ-ONLY. Don't MERGE / CREATE / SET /
  DELETE in a retrieval Cypher file.
- Every `GraphEvidence` must carry at least one
  `source_document_id`; the verdict engine requires provenance.
- `rerank(...)` is pure: same inputs, same order. No network, no
  random sampling, no learned model in v1. See ADR-0007.

## Testing

```bash
uv run --package civic-retrieval pytest services/retrieval/tests/ -q
```
