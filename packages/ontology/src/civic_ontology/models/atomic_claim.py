"""AtomicClaim — canonical contract (plan lines 249-270)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .common import TimeScope

ClaimType = Literal[
    "vote_cast",
    "bill_sponsorship",
    "office_held",
    "committee_membership",
    "committee_attendance",
    "statement_about_formal_action",
    "election_result",
]

Checkability = Literal[
    "checkable",
    "non_checkable",
    "insufficient_time_scope",
    "insufficient_entity_resolution",
]

VoteValue = Literal["for", "against", "abstain"]


class AtomicClaim(BaseModel):
    """Decomposed, checkability-classified claim awaiting verdict."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    claim_id: UUID
    raw_text: str
    normalized_text: str
    claim_type: ClaimType
    speaker_person_id: UUID | None
    target_person_id: UUID | None
    bill_id: UUID | None
    committee_id: UUID | None
    office_id: UUID | None
    vote_value: VoteValue | None
    party_id: UUID | None
    expected_seats: int | None
    expect_passed_threshold: bool | None
    time_scope: TimeScope
    checkability: Checkability
    created_at: datetime = Field(description="ISO-8601 datetime when the claim record was created.")
