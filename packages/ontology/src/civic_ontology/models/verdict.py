"""Verdict — canonical contract (plan lines 272-292)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .common import Confidence

VerdictStatus = Literal[
    "supported",
    "contradicted",
    "mixed",
    "insufficient_evidence",
    "non_checkable",
]


class Verdict(BaseModel):
    """Verification engine output for a single AtomicClaim."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    verdict_id: UUID
    claim_id: UUID
    status: VerdictStatus
    confidence: Confidence
    summary: str
    needs_human_review: bool
    model_version: str
    ruleset_version: str
    created_at: datetime
