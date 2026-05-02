"""Claim-family classifier.

Maps a :class:`~civic_claim_decomp.decomposer.DecompositionResult` to one of the
``ClaimFamily`` literals defined in the V2 ``Declaration`` model.

Decision order (highest-priority first):

1. ``formal_action``  — any claim whose ``claim_type`` is a direct formal-action
   indicator (``vote_cast``, ``bill_sponsorship``, ``committee_attendance``).
2. ``position_claim`` — any claim whose ``claim_type == "office_held"`` or
   ``"committee_membership"`` (role-holding, not action).
3. ``unknown``        — nothing matched (no claims, or an unrecognised set of
   claim types). Future heuristics (rhetoric detection, policy keyword matching)
   will upgrade relevant cases to ``rhetorical`` / ``policy_claim`` / ``electoral_claim``.

``electoral_claim`` and ``policy_claim`` are reserved for future classifiers that
examine utterance text directly (not just structured claim types).

No side effects. Stateless.
"""

from __future__ import annotations

from typing import Iterable, Literal

from civic_ontology.models.atomic_claim import ClaimType
from civic_ontology.models.declaration import ClaimFamily

from .decomposer import DecompositionResult

__all__ = ["classify_family", "FORMAL_ACTION_CLAIM_TYPES", "POSITION_CLAIM_TYPES"]

FORMAL_ACTION_CLAIM_TYPES: frozenset[ClaimType] = frozenset(
    {"vote_cast", "bill_sponsorship", "committee_attendance"}
)

POSITION_CLAIM_TYPES: frozenset[ClaimType] = frozenset(
    {"office_held", "committee_membership"}
)


def classify_family(result: DecompositionResult) -> ClaimFamily:
    """Return the ``ClaimFamily`` for a full :class:`DecompositionResult`.

    Uses only claim_type signals from the rule/LLM layer. Text-based
    family detection (electoral, policy, rhetoric) is deferred to future work.
    """
    types: Iterable[ClaimType] = (c.claim_type for c in result.claims)
    return _classify_from_types(list(types))


def _classify_from_types(claim_types: list[ClaimType]) -> ClaimFamily:
    if not claim_types:
        return "unknown"

    type_set = set(claim_types)

    if type_set & FORMAL_ACTION_CLAIM_TYPES:
        return "formal_action"

    if type_set & POSITION_CLAIM_TYPES:
        return "position_claim"

    return "unknown"


# Expose the inner helper for unit tests that build claim-type lists directly.
classify_family_from_types = _classify_from_types
