"""Declaration — a first-class political utterance (V2 data model)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

SourceKind = Literal[
    "plenum_transcript",
    "committee_transcript",
    "official_release",
    "interview",
    "social_post",
    "other",
]

ClaimFamily = Literal[
    "formal_action",
    "position_claim",
    "electoral_claim",
    "policy_claim",
    "rhetorical",
    "unknown",
]

DeclarationCheckability = Literal[
    "checkable_formal_action",
    "partially_checkable",
    "not_checkable",
    "insufficient_time_scope",
    "insufficient_entity_resolution",
]


class Declaration(BaseModel):
    """A political utterance stored independently from verdicts and official records.

    The speaker's statement is one object; the official record it may refer to is
    another; the judgment connecting them is a third (AttributionEdge).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    declaration_id: UUID
    speaker_person_id: UUID | None
    utterance_text: str
    utterance_language: str
    utterance_time: datetime | None
    source_document_id: UUID
    source_kind: SourceKind
    quoted_span: str | None
    canonicalized_text: str | None
    claim_family: ClaimFamily
    checkability: DeclarationCheckability
    derived_atomic_claim_ids: list[UUID]
    created_at: datetime
