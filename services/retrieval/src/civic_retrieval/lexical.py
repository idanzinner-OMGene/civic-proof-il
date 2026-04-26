"""Lexical retrieval over the OpenSearch ``evidence_spans`` index.

Default: BM25 over ``text`` / ``normalized_text`` fields.
Optional: vector kNN retrieval once an embedding model is approved.
Both paths are wired through :class:`LexicalRetriever`; vector is OFF
until the operator sets ``CIVIC_RETRIEVAL_VECTOR=1`` and plugs in a
concrete ``Embedder``.

For tests we ship :class:`MockLexicalRetriever` which returns canned
evidence without touching the network. The OpenSearch mapping delta
for vector support is attached as a migration delta; applying it is
gated on embedding-dep approval (see W2-B2 notes in the plan).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol

__all__ = [
    "LexicalEvidence",
    "LexicalRetriever",
    "MockLexicalRetriever",
    "Embedder",
]


@dataclass(frozen=True, slots=True)
class LexicalEvidence:
    span_id: str
    document_id: str
    text: str
    source_tier: int
    score: float
    properties: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "document_id": self.document_id,
            "text": self.text,
            "source_tier": self.source_tier,
            "score": self.score,
            "properties": dict(self.properties),
        }


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class LexicalRetriever:
    """OpenSearch-backed retriever.

    ``client`` is any object exposing the opensearch-py search surface:
    ``client.search(index=..., body=...)`` returning the usual
    ``{"hits": {"hits": [...]}}`` shape. Passing a stub in tests keeps
    coverage fast and offline.
    """

    def __init__(
        self,
        client: Any,
        *,
        index: str = "evidence_spans",
        embedder: Embedder | None = None,
        vector_enabled: bool | None = None,
    ) -> None:
        self._client = client
        self._index = index
        self._embedder = embedder
        if vector_enabled is None:
            vector_enabled = os.environ.get("CIVIC_RETRIEVAL_VECTOR", "0") == "1"
        self._vector_enabled = vector_enabled

    def search(
        self,
        query_text: str,
        *,
        top_k: int = 20,
        filters: Mapping[str, Any] | None = None,
    ) -> list[LexicalEvidence]:
        body = self._build_body(query_text, top_k=top_k, filters=filters)
        resp = self._client.search(index=self._index, body=body)
        return _unpack_hits(resp)

    def _build_body(
        self,
        query_text: str,
        *,
        top_k: int,
        filters: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query_text:
            must.append(
                {
                    "multi_match": {
                        "query": query_text,
                        "fields": ["text^2", "normalized_text"],
                        "type": "best_fields",
                    }
                }
            )
        filter_clauses: list[dict[str, Any]] = []
        for key, value in (filters or {}).items():
            if value is None:
                continue
            filter_clauses.append({"term": {key: value}})
        body: dict[str, Any] = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": must or [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
        }
        if self._vector_enabled and self._embedder is not None and query_text:
            vec = self._embedder.embed(query_text)
            body["knn"] = {
                "field": "embedding",
                "query_vector": vec,
                "k": top_k,
                "num_candidates": max(top_k * 4, 100),
            }
        return body


def _unpack_hits(response: Mapping[str, Any]) -> list[LexicalEvidence]:
    hits = (response.get("hits") or {}).get("hits") or []
    out: list[LexicalEvidence] = []
    for hit in hits:
        src = hit.get("_source") or {}
        out.append(
            LexicalEvidence(
                span_id=str(src.get("span_id") or hit.get("_id") or ""),
                document_id=str(src.get("document_id") or ""),
                text=str(src.get("text") or ""),
                source_tier=int(src.get("source_tier") or 2),
                score=float(hit.get("_score") or 0.0),
                properties={
                    k: v
                    for k, v in src.items()
                    if k not in {"span_id", "document_id", "text", "source_tier"}
                },
            )
        )
    return out


class MockLexicalRetriever:
    """Offline retriever used in tests and canvas demos.

    Accepts a list of :class:`LexicalEvidence` at construction time and
    returns them in order on every ``search`` call. Parameters are
    ignored — this is NOT for production.
    """

    def __init__(self, results: Iterable[LexicalEvidence]) -> None:
        self._results = list(results)

    def search(
        self,
        query_text: str,
        *,
        top_k: int = 20,
        filters: Mapping[str, Any] | None = None,
    ) -> list[LexicalEvidence]:
        return list(self._results[:top_k])
