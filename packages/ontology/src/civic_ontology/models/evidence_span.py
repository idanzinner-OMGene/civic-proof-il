"""EvidenceSpan — canonical contract (plan lines 294-308)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .common import SourceTier


class EvidenceSpan(BaseModel):
    """Provenance span supporting or contradicting a claim."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    span_id: UUID
    document_id: UUID
    source_tier: SourceTier
    source_type: str
    url: str
    archive_uri: str
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    captured_at: datetime
