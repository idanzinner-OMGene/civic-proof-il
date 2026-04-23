"""Phase-2 committee-session attendance adapter.

Reads ``KNS_CmtSessionAttendance``; normalizes into
:class:`NormalizedAttendanceEvent` bundles that include the
AttendanceEvent node and the set of Persons who attended.
"""

from __future__ import annotations

from .normalize import NormalizedAttendanceEvent, normalize_attendance
from .parse import parse_attendance
from .upsert import upsert_attendance

__all__ = [
    "NormalizedAttendanceEvent",
    "normalize_attendance",
    "parse_attendance",
    "upsert_attendance",
]
