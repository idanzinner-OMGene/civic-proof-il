"""Graph retrieval — parameterized Cypher templates per claim_type.

One query per family. Each returns canonical node IDs plus provenance
metadata so the verdict engine can explain its decision and the
reviewer can trace it back to a source document.

The Cypher templates live in ``infra/neo4j/retrieval/<claim_type>.cypher``
as external files so ops can edit them without a code deploy; this
module parses them at import time for fast reuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

__all__ = [
    "GraphEvidence",
    "GraphRetriever",
    "run_graph_retrieval",
    "TEMPLATE_DIR",
]


TEMPLATE_DIR = (
    Path(__file__).resolve().parents[4] / "infra" / "neo4j" / "retrieval"
)


@dataclass(frozen=True, slots=True)
class GraphEvidence:
    """One structured-fact result row from the graph retrieval layer."""

    claim_type: str
    node_ids: Mapping[str, str]
    properties: Mapping[str, Any]
    source_document_ids: tuple[str, ...] = field(default_factory=tuple)
    source_tier: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_type": self.claim_type,
            "node_ids": dict(self.node_ids),
            "properties": dict(self.properties),
            "source_document_ids": list(self.source_document_ids),
            "source_tier": self.source_tier,
        }


def _load_template(claim_type: str) -> str:
    path = TEMPLATE_DIR / f"{claim_type}.cypher"
    if not path.is_file():
        raise FileNotFoundError(
            f"no graph retrieval template for claim_type {claim_type!r} at {path}"
        )
    return path.read_text(encoding="utf-8")


class GraphRetriever:
    """Thin wrapper over a neo4j driver that dispatches by claim_type.

    Constructed with a driver-like object; tests pass a fake session
    that exposes ``session()`` / ``run()`` / iteration semantics.
    """

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    def retrieve(
        self,
        claim_type: str,
        *,
        params: Mapping[str, Any],
    ) -> list[GraphEvidence]:
        template = _load_template(claim_type)
        results: list[GraphEvidence] = []
        with self._driver.session() as session:
            for record in session.run(template, **params):
                results.append(_record_to_evidence(claim_type, record))
        return results


def _record_to_evidence(claim_type: str, record: Any) -> GraphEvidence:
    """Translate a Neo4j record into a :class:`GraphEvidence`.

    The Cypher templates must RETURN at least:
      - ``node_ids`` as a MAP of slot → id,
      - ``properties`` as a MAP of fact properties,
      - ``source_document_ids`` as a LIST of document UUIDs,
      - ``source_tier`` as an INT.

    Missing keys default to empty / 1 to match Tier-1 ingestion.
    """

    def _get(key: str, default: Any) -> Any:
        try:
            value = record[key]
        except (KeyError, IndexError, TypeError):
            value = None
        return default if value is None else value

    node_ids = _get("node_ids", {})
    properties = _get("properties", {})
    sdi = _get("source_document_ids", [])
    tier = _get("source_tier", 1)
    return GraphEvidence(
        claim_type=claim_type,
        node_ids={k: str(v) for k, v in dict(node_ids).items()},
        properties=dict(properties),
        source_document_ids=tuple(str(x) for x in sdi),
        source_tier=int(tier),
    )


def run_graph_retrieval(
    driver: Any,
    claim_type: str,
    params: Mapping[str, Any],
) -> list[GraphEvidence]:
    """Ergonomic one-shot entry point."""

    return GraphRetriever(driver).retrieve(claim_type, params=params)
