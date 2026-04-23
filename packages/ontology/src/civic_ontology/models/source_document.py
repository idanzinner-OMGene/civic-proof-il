"""SourceDocument — a captured document stored in the archive."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .common import SourceTier


class SourceDocument(BaseModel):
    """Captured source document (HTML, PDF, JSON, CSV, text)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    document_id: UUID
    source_family: str
    source_tier: SourceTier
    source_type: str
    url: str
    archive_uri: str
    content_sha256: str
    captured_at: datetime
    language: str
    title: str
    body: str
