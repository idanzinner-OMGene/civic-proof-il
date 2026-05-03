"""V2 declaration verification — Stage A (v1 record alignment) plus Stage B (relation edges).

Stage A reuses :meth:`VerifyPipeline.verify` on the declaration utterance text to obtain
per-claim v1 provenance bundles. Stage B maps each bundle to an :class:`AttributionEdge`
via :mod:`civic_verification.attribution_judge` and :mod:`civic_verification.relation_rules`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from civic_ontology.models.attribution import AttributionEdge, RelationType
from civic_ontology.models.declaration import Declaration

from . import relation_rules
from .attribution_judge import build_attribution_edge

if TYPE_CHECKING:
    from api.routers.pipeline import VerifyPipeline
    from civic_claim_decomp.declaration_decomposer import DeclarationDecompositionResult
    from civic_claim_decomp.decomposer import DecomposedClaim

logger = logging.getLogger(__name__)

Language = Literal["he", "en"]

_REVIEW_TRIGGER_RELATIONS: frozenset[RelationType] = frozenset(
    {
        "overstates",
        "underspecifies",
        "time_scope_mismatch",
        "entity_ambiguous",
        "contradicted_by",
    }
)


@dataclass(frozen=True, slots=True)
class DeclarationVerificationResult:
    """Structured output of :meth:`DeclarationVerifier.verify` (declaration + v1 + v2 layers)."""

    declaration: Declaration
    claims: list[DecomposedClaim] = field(default_factory=list)
    claim_verdicts: list[dict[str, Any]] = field(default_factory=list)
    attribution_edges: list[AttributionEdge] = field(default_factory=list)
    overall_relation: RelationType = "not_checkable_against_record"

    def as_dict(self) -> dict[str, Any]:
        """JSON-oriented aggregate for API-style responses."""

        claims_out: list[dict[str, Any]] = []
        for c in self.claims:
            claims_out.append(
                {
                    "claim_id": str(c.claim_id),
                    "raw_text": c.raw_text,
                    "normalized_text": c.normalized_text,
                    "claim_type": c.claim_type,
                    "slots": dict(c.slots),
                    "time_phrase": c.time_phrase,
                    "method": c.method,
                    "source_rule": c.source_rule,
                }
            )
        return {
            "declaration": self.declaration.model_dump(mode="json"),
            "claims": claims_out,
            "claim_verdicts": list(self.claim_verdicts),
            "attribution_edges": [e.model_dump(mode="json") for e in self.attribution_edges],
            "overall_relation": self.overall_relation,
        }


class DeclarationVerifier:
    """Runs v1 verification on a declaration utterance and emits attribution judgments."""

    def __init__(self, pipeline: VerifyPipeline, review_connection: Any | None = None) -> None:
        self._pipeline = pipeline
        self._review_connection = review_connection

    def verify(
        self,
        decomp_result: DeclarationDecompositionResult,
        *,
        language: Language = "he",
    ) -> DeclarationVerificationResult:
        """Verify ``decomp_result`` by re-running the v1 pipeline on the utterance text."""

        text = decomp_result.declaration.utterance_text
        bundles = self._pipeline.verify(text, language=language)
        claims = decomp_result.claims
        paired_bundles: list[dict[str, Any]] = []
        attribution_edges: list[AttributionEdge] = []
        for claim, bundle in zip(claims, bundles, strict=False):
            paired_bundles.append(bundle)
            verdict = bundle["verdict"]
            status = str(verdict["status"])
            conf = verdict["confidence"]
            if isinstance(conf, Mapping):
                overall_raw = conf.get("overall", 0.0)
            else:
                overall_raw = getattr(conf, "overall", 0.0)
            overall = float(overall_raw)
            needs_hr = bool(verdict.get("needs_human_review", False))
            reasons = tuple(verdict.get("reasons") or ())
            top_evidence = tuple(bundle.get("top_evidence") or ())
            lexical_hits = sum(1 for e in top_evidence if e.get("kind") == "lexical")
            claim_meta = bundle.get("claim") or {}
            checkability = str(claim_meta.get("checkability", ""))
            edge = build_attribution_edge(
                declaration_id=decomp_result.declaration.declaration_id,
                claim_id=claim.claim_id,
                claim_type=claim.claim_type,
                verdict_status=status,
                checkability=checkability,
                confidence_overall=overall,
                top_evidence=top_evidence,
                reasons=reasons,
                lexical_hits=lexical_hits,
                needs_human_review=needs_hr,
            )
            attribution_edges.append(edge)
        overall_relation = relation_rules.worst_relation(e.relation_type for e in attribution_edges)
        if self._review_connection is not None and overall_relation in _REVIEW_TRIGGER_RELATIONS:
            try:
                from civic_review import open_review_task

                payload = self._build_review_payload(
                    declaration_id=decomp_result.declaration.declaration_id,
                    overall_relation=overall_relation,
                    attribution_edges=attribution_edges,
                    derived_claim_ids=list(decomp_result.declaration.derived_atomic_claim_ids),
                    utterance_text=decomp_result.declaration.utterance_text,
                )
                open_review_task(
                    self._review_connection,
                    kind="declaration",
                    payload=payload,
                    priority=1,
                )
            except Exception:
                logger.exception("declaration review task enqueue failed")
        return DeclarationVerificationResult(
            declaration=decomp_result.declaration,
            claims=list(claims),
            claim_verdicts=paired_bundles,
            attribution_edges=attribution_edges,
            overall_relation=overall_relation,
        )

    def _build_review_payload(
        self,
        *,
        declaration_id: UUID,
        overall_relation: RelationType,
        attribution_edges: list[AttributionEdge],
        derived_claim_ids: list[UUID],
        utterance_text: str,
    ) -> dict[str, Any]:
        """Shape the Postgres JSON payload for a declaration-scoped review task."""

        truncated = utterance_text if len(utterance_text) <= 500 else utterance_text[:500]
        return {
            "declaration_id": str(declaration_id),
            "overall_relation": overall_relation,
            "attribution_edges": [e.model_dump(mode="json") for e in attribution_edges],
            "derived_claim_ids": [str(x) for x in derived_claim_ids],
            "utterance_text": truncated,
        }
