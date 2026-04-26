"""Neo4j upsert for :class:`NormalizedAttendanceEvent`.

Phase-2.5 populates per-MK attendance edges. For each attendee:

1. MERGE a Person stub (same pattern as votes / positions / committee
   memberships — Tier-1 people attributes may not be ingested yet).
2. MERGE the ``(:Person)-[:ATTENDED]->(:AttendanceEvent)`` edge via
   ``attended.cypher``, which requires a ``presence`` property.

``presence`` is always ``"present"`` in v1; the oknesset pipeline
does not distinguish absentees or partial attendance.
"""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedAttendanceEvent

__all__ = ["upsert_attendance"]

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

ATTENDANCE_EVENT_TEMPLATE = UPSERT_ROOT / "attendance_event_upsert.cypher"
PERSON_TEMPLATE = UPSERT_ROOT / "person_upsert.cypher"
ATTENDED_REL_TEMPLATE = UPSERT_ROOT / "relationships" / "attended.cypher"

_VALID_PRESENCE = {"present", "absent", "partial"}


def upsert_attendance(event: NormalizedAttendanceEvent) -> dict:
    run_upsert(
        ATTENDANCE_EVENT_TEMPLATE,
        {
            "attendance_event_id": str(event.attendance_event_id),
            "committee_id": str(event.committee_id),
            "occurred_at": event.occurred_at,
        },
    )
    edge_count = 0
    for attendee in event.attendees:
        person_id = getattr(attendee, "person_id", None) or (
            attendee.get("person_id") if isinstance(attendee, dict) else None
        )
        presence = getattr(attendee, "presence", None) or (
            attendee.get("presence") if isinstance(attendee, dict) else None
        )
        if person_id is None or presence not in _VALID_PRESENCE:
            continue
        run_upsert(
            PERSON_TEMPLATE,
            {
                "person_id": str(person_id),
                "canonical_name": None,
                "hebrew_name": None,
                "english_name": None,
                "external_ids": None,
                "source_tier": 2,
            },
        )
        run_upsert(
            ATTENDED_REL_TEMPLATE,
            {
                "person_id": str(person_id),
                "attendance_event_id": str(event.attendance_event_id),
                "presence": presence,
            },
        )
        edge_count += 1
    return {
        "attendance_event_id": str(event.attendance_event_id),
        "attendees": len(event.attendees),
        "attended_edges": edge_count,
    }
