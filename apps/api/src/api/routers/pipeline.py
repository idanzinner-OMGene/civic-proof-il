"""Dependency-injection seams for the /claims/verify pipeline.

The router is deliberately decoupled from the concrete Postgres /
Neo4j / OpenSearch connection objects; it talks to a
:class:`VerifyPipeline` interface and FastAPI's dependency system
supplies either the real or a stub implementation. Tests override
``get_pipeline`` to supply deterministic fakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol

import psycopg
from civic_claim_decomp import decompose
from civic_claim_decomp.checkability import CheckabilityInputs, classify
from civic_claim_decomp.decomposer import DecomposedClaim
from civic_retrieval import (
    GraphEvidence,
    LexicalEvidence,
    RerankScore,
    rerank,
)
from civic_temporal import normalize_time_scope
from civic_verification import VerdictInputs, bundle_provenance, decide_verdict

Language = Literal["he", "en"]


class GraphRetriever(Protocol):
    def retrieve(self, claim_type: str, *, params: dict[str, Any]) -> list[GraphEvidence]: ...


class LexicalRetriever(Protocol):
    def search(
        self,
        query_text: str,
        *,
        top_k: int = 20,
        filters: Mapping[str, Any] | None = None,
    ) -> list[LexicalEvidence]: ...


class EntityResolver(Protocol):
    def resolve(self, claim: DecomposedClaim) -> dict[str, str]:
        """Return a map of slot_name -> resolver_status."""


@dataclass
class VerifyPipeline:
    """Composes decomposition → resolution → retrieval → verdict.

    Every collaborator is optional so the route can respond even when
    backing stores are offline (the verdict engine abstains with
    ``insufficient_evidence`` when no evidence is retrieved).
    """

    graph: GraphRetriever | None = None
    lexical: LexicalRetriever | None = None
    resolver: EntityResolver | None = None
    default_language: Language = "he"
    review_connection: psycopg.Connection | None = None

    def verify(self, statement: str, language: Language | None = None) -> list[dict[str, Any]]:
        lang: Language = language or self.default_language
        result = decompose(statement, lang)
        bundles: list[dict[str, Any]] = []
        for claim in result.claims:
            resolver_status = self._resolver_status(claim)
            scope = normalize_time_scope(claim.time_phrase, language=lang)
            checkability = classify(
                CheckabilityInputs(
                    claim_type=claim.claim_type,
                    slots=claim.slots,
                    slot_resolver_status=resolver_status,
                    time_granularity=scope.granularity,
                )
            )
            ranked = self._retrieve(claim)
            outcome = decide_verdict(
                VerdictInputs(
                    claim_id=str(claim.claim_id),
                    claim_type=claim.claim_type,
                    checkability=checkability,
                    ranked_evidence=ranked,
                    expected_vote_value=claim.slots.get("vote_value"),
                    claim_time_scope=scope.model_dump(),
                )
            )
            if self.review_connection is not None:
                from civic_review.conflict import maybe_open_conflict_task

                maybe_open_conflict_task(
                    self.review_connection,
                    claim_id=str(claim.claim_id),
                    outcome=outcome,
                    ranked=ranked,
                )
            bundle = bundle_provenance(
                outcome,
                ranked,
                claim_id=str(claim.claim_id),
                claim_type=claim.claim_type,
            )
            payload = bundle.as_dict()
            payload["claim"] = {
                "claim_id": str(claim.claim_id),
                "claim_type": claim.claim_type,
                "normalized_text": claim.normalized_text,
                "slots": claim.slots,
                "time_phrase": claim.time_phrase,
                "time_scope": scope.model_dump(),
                "checkability": checkability,
                "method": claim.method,
            }
            bundles.append(payload)
        return bundles

    def _resolver_status(self, claim: DecomposedClaim) -> dict[str, str]:
        if self.resolver is None:
            status: dict[str, str] = {}
            for slot, value in claim.slots.items():
                if value is not None:
                    status[slot] = "resolved"
            return status
        try:
            return self.resolver.resolve(claim)
        except Exception:  # noqa: BLE001
            return {}

    def _retrieve(self, claim: DecomposedClaim) -> list[RerankScore]:
        graph_hits: list[GraphEvidence] = []
        lex_hits: list[LexicalEvidence] = []
        if self.graph is not None:
            try:
                graph_hits = self.graph.retrieve(claim.claim_type, params=claim.slots)
            except Exception:  # noqa: BLE001
                graph_hits = []
        if self.lexical is not None:
            try:
                lex_hits = self.lexical.search(claim.normalized_text)
            except Exception:  # noqa: BLE001
                lex_hits = []
        combined: list[Any] = [*graph_hits, *lex_hits]
        return rerank(combined, claim_type=claim.claim_type)


_default_pipeline: VerifyPipeline = VerifyPipeline()


def get_pipeline() -> VerifyPipeline:
    return _default_pipeline


def set_pipeline(pipeline: VerifyPipeline) -> None:
    """Swap the process-wide pipeline (used by wiring + tests)."""

    global _default_pipeline
    _default_pipeline = pipeline


def reset_pipeline() -> None:
    """Restore the default offline pipeline (used after lifespan shutdown)."""

    global _default_pipeline
    _default_pipeline = VerifyPipeline()
