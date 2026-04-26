"""civic_retrieval — graph + lexical retrieval for the Phase-4 pipeline.

Three layers:

* :mod:`civic_retrieval.graph` — structured-fact retrieval from Neo4j
  via parameterized Cypher templates, one per claim_type.
* :mod:`civic_retrieval.lexical` — BM25 + optional vector retrieval
  from the OpenSearch ``evidence_spans`` index (W2-B2).
* :mod:`civic_retrieval.rerank` — deterministic reranker combining
  source tier, directness, temporal alignment, entity resolution, and
  cross-source consistency (W2-B3).

Every layer returns typed ``Evidence`` records so downstream verdict
engine (W2-B4) and provenance bundler (W2-B5) share one wire shape.
"""

from __future__ import annotations

from .graph import GraphEvidence, GraphRetriever, run_graph_retrieval
from .lexical import LexicalEvidence, LexicalRetriever, MockLexicalRetriever
from .rerank import Evidence, RerankScore, rerank

__all__ = [
    "Evidence",
    "GraphEvidence",
    "GraphRetriever",
    "LexicalEvidence",
    "LexicalRetriever",
    "MockLexicalRetriever",
    "RerankScore",
    "rerank",
    "run_graph_retrieval",
]
