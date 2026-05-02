"""PositionTerm — time-bounded role holding (V2 data model)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PositionTerm(BaseModel):
    """Time-bounded holding of an Office by a Person.

    Used for date-aware verification of office claims — "served as minister" is
    checked against time-bounded holdings, not static labels.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    position_term_id: UUID
    person_id: UUID
    office_id: UUID
    appointing_body: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    is_acting: bool
    source_document_id: UUID | None
    created_at: datetime
