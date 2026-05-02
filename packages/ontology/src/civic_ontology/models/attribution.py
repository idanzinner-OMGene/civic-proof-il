"""AttributionEdge — judgment connecting a Declaration to a formal record (V2 data model)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ToObjectType = Literal[
    "VoteEvent",
    "Bill",
    "PositionTerm",
    "GovernmentDecision",
    "ElectionResult",
    "AtomicClaim",
]

RelationType = Literal[
    "supported_by",
    "contradicted_by",
    "overstates",
    "underspecifies",
    "time_scope_mismatch",
    "entity_ambiguous",
    "not_checkable_against_record",
]

ConfidenceBand = Literal["high", "medium", "low", "uncertain"]

ReviewStatus = Literal["pending", "confirmed", "rejected", "needs_human_review"]


class AttributionEdge(BaseModel):
    """Persists the judgment connecting a Declaration to a formal record or claim.

    This is Stage B verification output: it records which formal record was matched
    and how the declaration relates to it.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    attribution_id: UUID
    from_declaration_id: UUID
    to_object_id: UUID
    to_object_type: ToObjectType
    relation_type: RelationType
    evidence_span_ids: list[UUID]
    confidence_band: ConfidenceBand
    review_status: ReviewStatus
    created_at: datetime
