"""VoteEvent — a specific vote instance on a Bill."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VoteEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    vote_event_id: UUID
    bill_id: UUID
    occurred_at: datetime
    vote_type: str | None = None
