"""Normalize ``KNS_CommitteeSession`` row → ``AttendanceEvent`` bundle.

Each committee session produces exactly one ``AttendanceEvent`` node
(the session occurred). The set of attendees is intentionally empty
on the Phase-2 feed — per-MK presence lives in the session protocol
and is reconstructed in Phase-3 via protocol parsing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


@dataclass(frozen=True, slots=True)
class NormalizedAttendanceEvent:
    attendance_event_id: uuid.UUID
    committee_id: uuid.UUID
    occurred_at: str | None
    knesset_number: int | None = None
    session_type: str | None = None
    session_url: str | None = None
    attendees: tuple[uuid.UUID, ...] = field(default=())


def normalize_attendance(row: dict) -> Iterable[NormalizedAttendanceEvent]:
    session_ext = row["session_id_external"]
    committee_ext = row["committee_id_external"]

    yield NormalizedAttendanceEvent(
        attendance_event_id=_ext_uuid(
            "knesset_attendance_event", session_ext
        ),
        committee_id=_ext_uuid("knesset_committee", committee_ext),
        occurred_at=row.get("occurred_at"),
        knesset_number=row.get("knesset_number"),
        session_type=row.get("session_type"),
        session_url=row.get("session_url"),
        attendees=(),
    )
