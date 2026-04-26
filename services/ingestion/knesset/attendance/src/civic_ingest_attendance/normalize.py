"""Normalize oknesset session row → :class:`NormalizedAttendanceEvent`.

Each session row always produces one ``AttendanceEvent`` node. If
``attended_mk_individual_ids`` is populated (a JSON-encoded list of
``mk_individual_id`` values), we resolve each to the canonical
``PersonID`` via the shared :class:`~civic_ingest.MkIndividualLookup`
and emit one :class:`NormalizedAttendee` per resolvable MK — those
become ``(:Person)-[:ATTENDED]->(:AttendanceEvent)`` edges at upsert
time.

Presence is always ``"present"`` in v1 — the oknesset pipeline
only records MKs detected as attending; absentees and partial
attendance are not distinguished on this source.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from civic_ingest import MkIndividualLookup

__all__ = [
    "NormalizedAttendanceEvent",
    "NormalizedAttendee",
    "PHASE2_UUID_NAMESPACE",
    "normalize_attendance",
]


PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


@dataclass(frozen=True, slots=True)
class NormalizedAttendee:
    person_id: uuid.UUID
    presence: str
    mk_individual_id: str


@dataclass(frozen=True, slots=True)
class NormalizedAttendanceEvent:
    attendance_event_id: uuid.UUID
    committee_id: uuid.UUID
    occurred_at: str | None
    knesset_number: int | None = None
    session_type: str | None = None
    session_url: str | None = None
    attendees: tuple[NormalizedAttendee, ...] = field(default=())


def _parse_attended_ids(raw: object) -> list[str]:
    if raw in (None, "", "[]"):
        return []
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]
    try:
        values = json.loads(str(raw))
    except (TypeError, ValueError):
        return []
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def normalize_attendance(
    row: dict,
    *,
    lookup: MkIndividualLookup | None = None,
) -> Iterable[NormalizedAttendanceEvent]:
    session_ext = row["session_id_external"]
    committee_ext = row["committee_id_external"]

    attendees: tuple[NormalizedAttendee, ...] = ()
    if lookup is not None:
        resolved: list[NormalizedAttendee] = []
        for mk_id in _parse_attended_ids(row.get("attended_mk_individual_ids_raw")):
            person_external = lookup.get(mk_id)
            if person_external is None:
                continue
            resolved.append(
                NormalizedAttendee(
                    person_id=_ext_uuid("knesset_person", person_external),
                    presence="present",
                    mk_individual_id=mk_id,
                )
            )
        attendees = tuple(resolved)

    yield NormalizedAttendanceEvent(
        attendance_event_id=_ext_uuid(
            "knesset_attendance_event", session_ext
        ),
        committee_id=_ext_uuid("knesset_committee", committee_ext),
        occurred_at=row.get("occurred_at"),
        knesset_number=row.get("knesset_number"),
        session_type=row.get("session_type"),
        session_url=row.get("session_url"),
        attendees=attendees,
    )
