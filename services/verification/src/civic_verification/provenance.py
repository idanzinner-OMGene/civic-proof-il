"""Provenance bundler + evidence summarization LLM seam.

The bundler packs a verdict decision and its top evidence into a
stable JSON payload the API can return and the reviewer UI can render
without a second round trip. An optional LLM summarizer drafts a
reviewer-facing ``uncertainty_note`` paragraph; the summarizer is
strictly narrative — it MUST NOT alter the verdict, confidence, or
status fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from civic_retrieval.graph import GraphEvidence
from civic_retrieval.lexical import LexicalEvidence
from civic_retrieval.rerank import RerankScore

from .engine import VerdictOutcome

__all__ = [
    "ProvenanceBundle",
    "UncertaintyBundler",
    "EvidenceSummarizer",
    "bundle_provenance",
]


@dataclass(frozen=True, slots=True)
class ProvenanceBundle:
    verdict: dict[str, Any]
    top_evidence: list[dict[str, Any]]
    uncertainty_note: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": dict(self.verdict),
            "top_evidence": list(self.top_evidence),
            "uncertainty_note": self.uncertainty_note,
        }


class EvidenceSummarizer(Protocol):
    """LLM seam for the reviewer-facing uncertainty note.

    The summarizer is called ONLY when the outcome has
    ``needs_human_review=True``. It receives a stable dict of verdict +
    top-evidence; it returns a single paragraph or ``None`` if it
    cannot produce one. The verdict decision is never rewritten — the
    return value is used verbatim as ``uncertainty_note``.
    """

    def summarize(self, payload: dict[str, Any]) -> str | None: ...


def _evidence_to_dict(score: RerankScore) -> dict[str, Any]:
    e = score.evidence
    if isinstance(e, GraphEvidence):
        body = {"kind": "graph", **e.as_dict()}
    elif isinstance(e, LexicalEvidence):
        body = {"kind": "lexical", **e.as_dict()}
    else:
        body = {"kind": "unknown"}
    body["scores"] = score.as_dict()
    return body


def bundle_provenance(
    outcome: VerdictOutcome,
    ranked: Sequence[RerankScore],
    *,
    claim_id: str,
    claim_type: str,
    top_k: int = 5,
    summarizer: EvidenceSummarizer | None = None,
) -> ProvenanceBundle:
    top = [_evidence_to_dict(r) for r in list(ranked)[:top_k]]
    verdict_payload: dict[str, Any] = {
        "claim_id": claim_id,
        "claim_type": claim_type,
        **outcome.as_dict(),
    }

    note: str | None = None
    if outcome.needs_human_review and summarizer is not None:
        try:
            note = summarizer.summarize(
                {"verdict": dict(verdict_payload), "top_evidence": list(top)}
            )
        except Exception:  # summarizer failures never break the verdict  # noqa: BLE001
            note = None
    return ProvenanceBundle(
        verdict=verdict_payload,
        top_evidence=top,
        uncertainty_note=note,
    )


class UncertaintyBundler:
    """Stateful variant that pins a summarizer and a top_k."""

    def __init__(self, *, summarizer: EvidenceSummarizer | None = None, top_k: int = 5) -> None:
        self.summarizer = summarizer
        self.top_k = top_k

    def __call__(
        self,
        outcome: VerdictOutcome,
        ranked: Sequence[RerankScore],
        *,
        claim_id: str,
        claim_type: str,
    ) -> ProvenanceBundle:
        return bundle_provenance(
            outcome,
            ranked,
            claim_id=claim_id,
            claim_type=claim_type,
            top_k=self.top_k,
            summarizer=self.summarizer,
        )
