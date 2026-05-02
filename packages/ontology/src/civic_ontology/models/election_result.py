"""ElectionResult — formal election result record (V2 data model)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ElectionResult(BaseModel):
    """Formal election result for a party or list.

    Tier 1 canonical source for seat, vote, and threshold claims.
    Party/list continuity across renames is handled by the normalizer
    before this record is created.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    election_result_id: UUID
    election_date: datetime | None
    list_party_id: UUID | None
    votes: int | None
    seats_won: int | None
    vote_share: float | None
    passed_threshold: bool | None
    source_document_id: UUID | None
    created_at: datetime
