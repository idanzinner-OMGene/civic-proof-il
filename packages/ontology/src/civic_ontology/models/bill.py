"""Bill — proposed or enacted legislation under a specific Knesset number."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Bill(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    bill_id: UUID
    title: str
    knesset_number: int = Field(ge=1)
    status: str | None = None
