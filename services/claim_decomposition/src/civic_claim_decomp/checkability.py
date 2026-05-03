"""Checkability classifier.

Maps ``(decomposed_claim, resolver_status, time_scope_granularity)`` to
one of the four :class:`civic_ontology.models.atomic_claim.Checkability`
enum values.

Decision order (strictest-first):

1. ``non_checkable`` if the claim_type is not one of the supported
   families (defensive — the decomposer only emits supported types, but
   the classifier re-checks to stay future-proof).
2. ``insufficient_entity_resolution`` if any required slot is empty
   (per :data:`civic_ontology.SLOT_TEMPLATES`), OR the entity-resolver
   returned ``ambiguous`` / ``unresolved`` for a required entity slot.
3. ``insufficient_time_scope`` if ``time_scope.granularity == "unknown"``
   for claim types that REQUIRE a time anchor (``vote_cast``,
   ``committee_attendance``). Other claim types tolerate unknown time.
4. ``checkable`` otherwise.
"""

from __future__ import annotations

from typing import Literal, Mapping

from civic_ontology import SLOT_TEMPLATES
from civic_ontology.claim_slots import validate_slots
from civic_ontology.models.atomic_claim import ClaimType

__all__ = ["CheckabilityInputs", "classify", "TIME_REQUIRED_CLAIM_TYPES"]


TIME_REQUIRED_CLAIM_TYPES: frozenset[ClaimType] = frozenset(
    {"vote_cast", "committee_attendance"}
)

ResolverStatus = Literal["resolved", "ambiguous", "unresolved", "not_applicable"]


class CheckabilityInputs:
    """Bag of inputs for ``classify``.

    ``slot_resolver_status`` maps slot name → resolver status. Slots not
    present in the map default to ``"not_applicable"``. Any slot listed
    in the per-claim_type required set that resolves to anything other
    than ``"resolved"`` counts against checkability.
    """

    __slots__ = ("claim_type", "slots", "slot_resolver_status", "time_granularity")

    def __init__(
        self,
        claim_type: str,
        slots: Mapping[str, object | None],
        slot_resolver_status: Mapping[str, ResolverStatus] | None = None,
        time_granularity: str = "unknown",
    ) -> None:
        self.claim_type = claim_type
        self.slots = dict(slots)
        self.slot_resolver_status = dict(slot_resolver_status or {})
        self.time_granularity = time_granularity


def classify(inputs: CheckabilityInputs) -> str:
    if inputs.claim_type not in SLOT_TEMPLATES:
        return "non_checkable"

    violations = validate_slots(inputs.claim_type, inputs.slots)
    if violations:
        return "insufficient_entity_resolution"

    tmpl = SLOT_TEMPLATES[inputs.claim_type]
    for slot in tmpl.required:
        status = inputs.slot_resolver_status.get(slot, "not_applicable")
        if status not in ("resolved", "not_applicable"):
            return "insufficient_entity_resolution"

    if inputs.claim_type in TIME_REQUIRED_CLAIM_TYPES:
        if inputs.time_granularity == "unknown":
            return "insufficient_time_scope"

    return "checkable"
