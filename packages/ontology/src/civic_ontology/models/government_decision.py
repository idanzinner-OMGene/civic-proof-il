"""GovernmentDecision — formal government decision record (V2 data model)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GovernmentDecision(BaseModel):
    """A formal government decision record.

    Tier 1 canonical source for government-decision claims. Government decisions
    are not bills or votes; they need their own node type.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    government_decision_id: UUID
    decision_number: str | None
    government_number: int | None
    decision_date: datetime | None
    title: str
    summary: str | None
    issuing_body: str | None
    source_document_id: UUID | None
    created_at: datetime
