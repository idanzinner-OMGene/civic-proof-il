"""Unit tests for the attendance adapter, pinned to the real recorded
cassette at ``tests/fixtures/phase2/cassettes/attendance/sample.csv``
(oknesset meeting-attendees mirror).

Phase 2.5 switched this adapter from Tier-1 OData JSON to a Tier-2
oknesset CSV because the OData endpoint does not expose per-MK
attendance — the oknesset pipeline parses session protocols and
publishes ``attended_mk_individual_ids`` on each session row.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import load_mk_individual_lookup, parse_csv_page
from civic_ingest_attendance.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_attendance,
)
from civic_ingest_attendance.parse import parse_attendance

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/attendance/sample.csv"
)


def _load():
    return parse_csv_page(SAMPLE.read_bytes())


def _lookup():
    return load_mk_individual_lookup()


def test_cassette_first_row_is_knesset_16_session():
    page = _load()
    assert len(page.value) == 50
    first = page.value[0]
    assert first["CommitteeSessionID"] == "64515"
    assert first["CommitteeID"] == "22"
    assert first["KnessetNum"] == "16"
    assert first["TypeDesc"] == "פתוחה"
    assert first["attended_mk_individual_ids"] == "[]"


def test_parse_yields_real_first_session_with_iso_datetime():
    rows = list(parse_attendance(_load()))
    assert len(rows) == 50
    r0 = rows[0]
    assert r0["session_id_external"] == "64515"
    assert r0["committee_id_external"] == "22"
    assert r0["knesset_number"] == 16
    assert r0["occurred_at"] == "2003-02-25T10:30:00"
    assert r0["session_type"] == "פתוחה"
    assert r0["attended_mk_individual_ids_raw"] == "[]"


def test_normalize_first_row_has_no_attendees_when_array_empty():
    row = next(iter(parse_attendance(_load())))
    events = list(normalize_attendance(row, lookup=_lookup()))
    assert len(events) == 1
    e = events[0]
    assert e.attendance_event_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_attendance_event:64515"
    )
    assert e.committee_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_committee:22"
    )
    assert e.attendees == ()
    assert e.session_type == "פתוחה"


def test_normalize_second_row_resolves_attendees_via_lookup():
    rows = list(parse_attendance(_load()))
    events = list(normalize_attendance(rows[1], lookup=_lookup()))
    assert len(events) == 1
    e = events[0]
    assert len(e.attendees) == 18  # 18 MKs in the captured array
    # The first MK_individual_id=736 resolves to PersonID=1039 via the
    # real mk_individual lookup; that UUID must match the people
    # adapter's namespace (same UUID5 on "knesset_person:1039").
    assert e.attendees[0].person_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_person:1039"
    )
    assert e.attendees[0].mk_individual_id == "736"
    assert all(a.presence == "present" for a in e.attendees)


def test_normalize_without_lookup_still_emits_event_without_attendees():
    """The adapter must tolerate callers that don't supply a lookup —
    useful for dry-run / schema-validation paths."""
    rows = list(parse_attendance(_load()))
    events = list(normalize_attendance(rows[1]))
    assert len(events) == 1
    assert events[0].attendees == ()


def test_all_cassette_attendees_resolve_through_real_lookup():
    """Full-corpus real-data check: every mk_individual_id that appears
    in the cassette's ``attended_mk_individual_ids`` arrays must resolve
    through the recorded mk_individual.csv lookup. If this ever flips,
    either the cassette or the lookup needs re-recording."""
    lookup = _lookup()
    unresolved: set[str] = set()
    for row in parse_attendance(_load()):
        for event in normalize_attendance(row, lookup=lookup):
            _ = event
        # re-walk the raw list to check raw vs resolved count
        raw = row.get("attended_mk_individual_ids_raw")
        import json as _json

        if raw and raw != "[]":
            for mk_id in _json.loads(raw):
                if str(mk_id) not in lookup:
                    unresolved.add(str(mk_id))
    assert unresolved == set()
