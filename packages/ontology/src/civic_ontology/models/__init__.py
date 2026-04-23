"""Pydantic v2 models for the civic ontology.

Every model here is the Python-side twin of a hand-written JSON Schema in
``data_contracts/jsonschemas``. The hand-written schemas are canonical; these
models exist to give Python callers a typed surface and to round-trip fixtures.
"""

from __future__ import annotations

from .atomic_claim import AtomicClaim
from .attendance_event import AttendanceEvent
from .bill import Bill
from .committee import Committee
from .common import Confidence, Granularity, OrgType, SourceTier, TimeScope
from .evidence_span import EvidenceSpan
from .membership_term import MembershipTerm
from .office import Office
from .party import Party
from .person import Person
from .source_document import SourceDocument
from .verdict import Verdict
from .vote_event import VoteEvent

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
    "SourceDocument",
    "SourceTier",
    "TimeScope",
    "Verdict",
    "VoteEvent",
]
