"""civic_verification — deterministic verdict engine, abstention policy,
five-axis confidence rubric, and provenance bundling.

No LLM involvement in the canonical verdict decision itself (plan rules
31-36). The ``UncertaintyBundler`` in :mod:`civic_verification.provenance`
exposes a narrow LLM seam used ONLY to draft a human-facing uncertainty
note; verdict + confidence + needs_human_review come entirely from the
deterministic rubric.
"""

from __future__ import annotations

from .attribution_judge import build_attribution_edge, determine_to_object_type
from .confidence import FiveAxisRubric, compute_confidence
from .declaration_verifier import DeclarationVerificationResult, DeclarationVerifier
from .engine import VerdictInputs, VerdictOutcome, decide_verdict
from .provenance import ProvenanceBundle, UncertaintyBundler, bundle_provenance
from .relation_rules import (
    RELATION_PRIORITY,
    determine_confidence_band,
    determine_relation,
    worst_relation,
)

__all__ = [
    "FiveAxisRubric",
    "DeclarationVerificationResult",
    "DeclarationVerifier",
    "ProvenanceBundle",
    "RELATION_PRIORITY",
    "UncertaintyBundler",
    "VerdictInputs",
    "VerdictOutcome",
    "build_attribution_edge",
    "bundle_provenance",
    "compute_confidence",
    "decide_verdict",
    "determine_confidence_band",
    "determine_relation",
    "determine_to_object_type",
    "worst_relation",
]
