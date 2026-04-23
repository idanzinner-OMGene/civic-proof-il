"""Office — government/parliamentary role a Person can hold."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

OfficeType = Literal["mk", "minister", "deputy_minister", "other"]


class Office(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    office_id: UUID
    canonical_name: str
    office_type: OfficeType
    scope: str | None = None
