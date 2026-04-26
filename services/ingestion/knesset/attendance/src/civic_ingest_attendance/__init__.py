"""Phase-2.5 committee-session attendance adapter.

Reads the oknesset ``kns_committeesession.csv`` mirror (Tier-2);
normalizes into :class:`NormalizedAttendanceEvent` bundles that include
the AttendanceEvent node and the resolved tuple of attending MKs.
Per-MK resolution goes through :class:`civic_ingest.MkIndividualLookup`
since upstream keys attendees by ``mk_individual_id``, not the
canonical ``PersonID``.
"""

from __future__ import annotations

from .normalize import (
    NormalizedAttendanceEvent,
    NormalizedAttendee,
    PHASE2_UUID_NAMESPACE,
    normalize_attendance,
)
from .parse import parse_attendance
from .upsert import upsert_attendance

__all__ = [
    "NormalizedAttendanceEvent",
    "NormalizedAttendee",
    "PHASE2_UUID_NAMESPACE",
    "normalize_attendance",
    "parse_attendance",
    "upsert_attendance",
]
