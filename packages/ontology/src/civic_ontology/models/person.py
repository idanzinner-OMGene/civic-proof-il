"""Person — minimal business-key + canonical-name model."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .common import SourceTier


class Person(BaseModel):
    """A real-world person (MK, minister, etc.) identified by UUID4."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    person_id: UUID
    canonical_name: str
    hebrew_name: str | None = None
    english_name: str | None = None
    external_ids: dict[str, str] | None = None
    source_tier: SourceTier | None = None
