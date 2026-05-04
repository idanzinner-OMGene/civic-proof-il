"""Per-claim_type slot templates.

Each ``claim_type`` enum value binds a
specific subset of the ``AtomicClaim`` nullable foreign-key slots as
REQUIRED, OPTIONAL, or FORBIDDEN. The wire-format contract
(``AtomicClaim`` schema) keeps every slot as a nullable required key; this
module adds the *per-type* invariants the decomposer + checkability
classifier must satisfy.

Example — ``vote_cast``:
    REQUIRED  {speaker_person_id, bill_id, vote_value}
    OPTIONAL  {time_scope}
    FORBIDDEN {target_person_id, committee_id, office_id}

``target_person_id`` is the *subject* of a third-person claim
("X voted against Y"); ``speaker_person_id`` is the *utterer* in a
reported-speech claim. For a direct vote claim we want the MK whose
vote we're checking, so ``speaker_person_id`` holds the subject.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Mapping

from .models.atomic_claim import ClaimType

__all__ = [
    "SlotName",
    "SlotRequirement",
    "SlotTemplate",
    "SLOT_TEMPLATES",
    "validate_slots",
]

SlotName = str  # one of the nullable-FK slots on AtomicClaim
SlotRequirement = str  # "required" | "optional" | "forbidden"

ALL_SLOTS: frozenset[SlotName] = frozenset(
    {
        "speaker_person_id",
        "target_person_id",
        "bill_id",
        "committee_id",
        "office_id",
        "vote_value",
        "party_id",
        "expected_seats",
        "expect_passed_threshold",
        "government_decision_id",
    }
)


@dataclass(frozen=True, slots=True)
class SlotTemplate:
    """Per-claim_type slot invariants."""

    claim_type: ClaimType
    required: FrozenSet[SlotName]
    optional: FrozenSet[SlotName]

    @property
    def forbidden(self) -> FrozenSet[SlotName]:
        return ALL_SLOTS - self.required - self.optional


SLOT_TEMPLATES: Mapping[ClaimType, SlotTemplate] = {
    "vote_cast": SlotTemplate(
        claim_type="vote_cast",
        required=frozenset({"speaker_person_id", "bill_id", "vote_value"}),
        optional=frozenset({"target_person_id"}),
    ),
    "bill_sponsorship": SlotTemplate(
        claim_type="bill_sponsorship",
        required=frozenset({"speaker_person_id", "bill_id"}),
        optional=frozenset({"target_person_id"}),
    ),
    "office_held": SlotTemplate(
        claim_type="office_held",
        required=frozenset({"speaker_person_id", "office_id"}),
        optional=frozenset({"target_person_id"}),
    ),
    "committee_membership": SlotTemplate(
        claim_type="committee_membership",
        required=frozenset({"speaker_person_id", "committee_id"}),
        optional=frozenset({"target_person_id"}),
    ),
    "committee_attendance": SlotTemplate(
        claim_type="committee_attendance",
        required=frozenset({"speaker_person_id", "committee_id"}),
        optional=frozenset({"target_person_id"}),
    ),
    "statement_about_formal_action": SlotTemplate(
        claim_type="statement_about_formal_action",
        required=frozenset({"speaker_person_id"}),
        optional=frozenset(
            {"target_person_id", "bill_id", "committee_id", "office_id", "vote_value"}
        ),
    ),
    "election_result": SlotTemplate(
        claim_type="election_result",
        required=frozenset({"party_id"}),
        optional=frozenset(
            {
                "speaker_person_id",
                "target_person_id",
                "expected_seats",
                "expect_passed_threshold",
            }
        ),
    ),
    "government_decision": SlotTemplate(
        claim_type="government_decision",
        required=frozenset({"government_decision_id"}),
        optional=frozenset(
            {
                "speaker_person_id",
                "target_person_id",
                "office_id",
            }
        ),
    ),
}


def validate_slots(
    claim_type: ClaimType, slots: Mapping[SlotName, object | None]
) -> list[str]:
    """Return a list of violation strings, or an empty list if valid.

    A slot is "present" iff ``slots[name]`` is not ``None``. Missing keys
    count as absent (None). The function never raises; it returns a list
    so the checkability classifier can decide the severity.
    """

    if claim_type not in SLOT_TEMPLATES:
        return [f"unknown claim_type: {claim_type!r}"]

    tmpl = SLOT_TEMPLATES[claim_type]
    violations: list[str] = []

    for req in tmpl.required:
        if slots.get(req) in (None, ""):
            violations.append(f"required slot {req!r} is empty for {claim_type}")

    for forb in tmpl.forbidden:
        if slots.get(forb) not in (None, ""):
            violations.append(f"forbidden slot {forb!r} is set for {claim_type}")

    return violations
