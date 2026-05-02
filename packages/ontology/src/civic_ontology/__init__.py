"""civic_ontology — canonical Pydantic v2 models + JSON Schema contracts.

Every model is re-exported here for ergonomic imports:

    from civic_ontology import AtomicClaim, Verdict, Person, ...

The hand-written JSON Schemas in ``data_contracts/jsonschemas/`` are the
canonical contracts; the Pydantic models in :mod:`civic_ontology.models`
are the Python-side twins. Drift is checked by
:mod:`civic_ontology.schemas` (see its module docstring).
"""

from __future__ import annotations

from .claim_slots import SLOT_TEMPLATES, SlotTemplate, validate_slots
from .models import (
    AtomicClaim,
    AttendanceEvent,
    AttributionEdge,
    Bill,
    ClaimFamily,
    Committee,
    ConfidenceBand,
    Confidence,
    Declaration,
    DeclarationCheckability,
    ElectionResult,
    EvidenceSpan,
    GovernmentDecision,
    Granularity,
    MembershipTerm,
    Office,
    OrgType,
    Party,
    Person,
    PositionTerm,
    RelationType,
    ReviewStatus,
    SourceDocument,
    SourceKind,
    SourceTier,
    TimeScope,
    ToObjectType,
    Verdict,
    VoteEvent,
)

__all__ = [
    "AtomicClaim",
    "AttendanceEvent",
    "AttributionEdge",
    "Bill",
    "ClaimFamily",
    "Committee",
    "ConfidenceBand",
    "Confidence",
    "Declaration",
    "DeclarationCheckability",
    "ElectionResult",
    "EvidenceSpan",
    "GovernmentDecision",
    "Granularity",
    "MembershipTerm",
    "Office",
    "OrgType",
    "Party",
    "Person",
    "PositionTerm",
    "RelationType",
    "ReviewStatus",
    "SLOT_TEMPLATES",
    "SlotTemplate",
    "SourceDocument",
    "SourceKind",
    "SourceTier",
    "TimeScope",
    "ToObjectType",
    "Verdict",
    "VoteEvent",
    "validate_slots",
]
