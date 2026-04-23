"""Party — political party a Person can be a member of."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Party(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    party_id: UUID
    canonical_name: str
    hebrew_name: str | None = None
    english_name: str | None = None
    abbreviation: str | None = None
