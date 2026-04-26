"""civic_verification — deterministic verdict engine, abstention policy,
five-axis confidence rubric, and provenance bundling.

No LLM involvement in the canonical verdict decision itself (plan rules
31-36). The ``UncertaintyBundler`` in :mod:`civic_verification.provenance`
exposes a narrow LLM seam used ONLY to draft a human-facing uncertainty
note; verdict + confidence + needs_human_review come entirely from the
deterministic rubric.
"""

from __future__ import annotations

from .confidence import FiveAxisRubric, compute_confidence
from .engine import VerdictInputs, VerdictOutcome, decide_verdict
from .provenance import ProvenanceBundle, UncertaintyBundler, bundle_provenance

__all__ = [
    "FiveAxisRubric",
    "ProvenanceBundle",
    "UncertaintyBundler",
    "VerdictInputs",
    "VerdictOutcome",
    "bundle_provenance",
    "compute_confidence",
    "decide_verdict",
]
