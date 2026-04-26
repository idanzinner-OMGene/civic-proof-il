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
    Bill,
    Committee,
    Confidence,
    EvidenceSpan,
    Granularity,
    MembershipTerm,
    Office,
    OrgType,
    Party,
    Person,
    SourceDocument,
    SourceTier,
    TimeScope,
    Verdict,
    VoteEvent,
)

__all__ = [
    "AtomicClaim",
    "AttendanceEvent",
    "Bill",
    "Committee",
    "Confidence",
    "EvidenceSpan",
    "Granularity",
    "MembershipTerm",
    "Office",
    "OrgType",
    "Party",
    "Person",
    "SLOT_TEMPLATES",
    "SlotTemplate",
    "SourceDocument",
    "SourceTier",
    "TimeScope",
    "Verdict",
    "VoteEvent",
    "validate_slots",
]
