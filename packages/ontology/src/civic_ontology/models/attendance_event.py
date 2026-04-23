"""AttendanceEvent — committee attendance record."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttendanceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    attendance_event_id: UUID
    committee_id: UUID
    occurred_at: datetime
