"""Committee — Knesset committee."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Committee(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    committee_id: UUID
    canonical_name: str
    hebrew_name: str | None = None
