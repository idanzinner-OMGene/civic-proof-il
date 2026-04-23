"""Neo4j upsert for NormalizedAttendanceEvent bundles."""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedAttendanceEvent

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

ATTENDANCE_EVENT_TEMPLATE = UPSERT_ROOT / "attendance_event_upsert.cypher"


def upsert_attendance(event: NormalizedAttendanceEvent) -> dict:
    run_upsert(
        ATTENDANCE_EVENT_TEMPLATE,
        {
            "attendance_event_id": str(event.attendance_event_id),
            "committee_id": str(event.committee_id),
            "occurred_at": event.occurred_at,
        },
    )
    return {
        "attendance_event_id": str(event.attendance_event_id),
        "attendees": len(event.attendees),
    }
