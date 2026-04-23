"""Unit tests for the attendance adapter, pinned to the first row of the
real committee-session cassette at
``tests/fixtures/phase2/cassettes/attendance/sample.json``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import parse_odata_page
from civic_ingest_attendance.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_attendance,
)
from civic_ingest_attendance.parse import parse_attendance

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/attendance/sample.json"
)


def _load():
    return parse_odata_page(SAMPLE.read_bytes())


def test_cassette_has_real_knesset_25_sessions():
    page = _load()
    assert len(page.value) == 20
    first = page.value[0]
    assert first["CommitteeSessionID"] == 2196141
    assert first["CommitteeID"] == 4185
    assert first["KnessetNum"] == 25


def test_parse_yields_real_first_session():
    rows = list(parse_attendance(_load()))
    assert len(rows) == 20
    r0 = rows[0]
    assert r0["session_id_external"] == "2196141"
    assert r0["committee_id_external"] == "4185"
    assert r0["occurred_at"].startswith("2022-")
    assert r0["session_type"] == "פתוחה"


def test_normalize_produces_attendance_event_without_embedded_attendees():
    row = next(iter(parse_attendance(_load())))
    events = list(normalize_attendance(row))
    assert len(events) == 1
    e = events[0]
    assert e.attendance_event_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_attendance_event:2196141"
    )
    assert e.committee_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_committee:4185"
    )
    assert e.attendees == ()  # real feed does not include attendees
    assert e.session_type == "פתוחה"
