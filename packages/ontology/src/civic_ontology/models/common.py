"""Shared primitives: SourceTier, TimeScope, Confidence, and enum literals."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceTier = Literal[1, 2, 3]
"""Canonical source-tier integer enum (plan lines 38-54)."""

Granularity = Literal["day", "month", "year", "term", "unknown"]

OrgType = Literal["party", "office", "committee"]


class TimeScope(BaseModel):
    """Temporal scope of a claim. Null start/end = open-ended on that side."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    start: str | None = Field(default=None, description="ISO-8601 datetime; null = open-ended start.")
    end: str | None = Field(default=None, description="ISO-8601 datetime; null = open-ended end.")
    granularity: Granularity


class Confidence(BaseModel):
    """Six-factor confidence vector; every factor is in [0, 1]."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source_authority: float = Field(ge=0.0, le=1.0)
    directness: float = Field(ge=0.0, le=1.0)
    temporal_alignment: float = Field(ge=0.0, le=1.0)
    entity_resolution: float = Field(ge=0.0, le=1.0)
    cross_source_consistency: float = Field(ge=0.0, le=1.0)
    overall: float = Field(ge=0.0, le=1.0)
