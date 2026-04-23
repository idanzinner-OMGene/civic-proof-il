"""Unit tests for the people adapter.

Assertions are pinned to the first row of the real recorded cassette
at ``tests/fixtures/phase2/cassettes/people/sample.json``. Re-recording
the cassette (``make record-cassettes``) may change upstream's first
row, which surfaces as a legitimate test failure — at that point
either the upstream drift is acceptable (update the pins) or it's a
bug (fix the adapter).
"""

from __future__ import annotations

from pathlib import Path

from civic_ingest import ODataPage, parse_odata_page
from civic_ingest_people.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_person,
)
from civic_ingest_people.parse import parse_persons

import uuid


REPO_ROOT = Path(__file__).resolve().parents[5]
SAMPLE = REPO_ROOT / "tests/fixtures/phase2/cassettes/people/sample.json"


def _load_page() -> ODataPage:
    return parse_odata_page(SAMPLE.read_bytes())


def test_cassette_has_expected_first_row_from_real_upstream():
    page = _load_page()
    assert len(page.value) == 100
    first = page.value[0]
    assert first["PersonID"] == 48
    assert first["FirstName"] == "ירדנה"
    assert first["LastName"] == "מלר-הורוביץ"
    assert first["IsCurrent"] is False


def test_cassette_covers_historical_mks_referenced_by_votes_cassette():
    """Votes CSV references PersonID=405 (Benjamin Elon, Knesset 16).

    The People cassette must include him so the People adapter can
    back-fill `hebrew_name` / `canonical_name` onto the stub Person
    node the votes adapter upserts. This pin is the regression test
    for the `$filter=IsCurrent eq true` removal on 2026-04-23.
    """
    page = _load_page()
    elon = next((r for r in page.value if r["PersonID"] == 405), None)
    assert elon is not None, "PersonID=405 missing — did someone re-add IsCurrent filter?"
    assert elon["FirstName"] == "בנימין"
    assert elon["LastName"] == "אלון"
    assert elon["IsCurrent"] is False


def test_parse_persons_pins_first_real_row():
    rows = list(parse_persons(_load_page()))
    assert len(rows) == 100
    r0 = rows[0]
    assert r0["person_id_external"] == "48"
    assert r0["first_name_he"] == "ירדנה"
    assert r0["last_name_he"] == "מלר-הורוביץ"
    assert r0["gender"] == "נקבה"
    assert r0["is_current"] is False


def test_parse_persons_drops_rows_missing_person_id():
    page = ODataPage(
        value=[{"FirstName": "x"}], next_link=None, total_count=0
    )
    assert list(parse_persons(page)) == []


def test_normalize_person_produces_person_only_from_real_row():
    rows = list(parse_persons(_load_page()))
    people = list(normalize_person(rows[0]))
    assert len(people) == 1
    p = people[0]
    assert p.hebrew_name == "ירדנה מלר-הורוביץ"
    assert p.canonical_name == "ירדנה מלר-הורוביץ"
    assert p.external_ids == {"knesset_person_id": "48"}
    assert p.is_current is False
    assert p.party is None
    assert p.office is None


def test_normalize_person_uses_deterministic_uuid_from_external_id():
    rows = list(parse_persons(_load_page()))
    p1 = next(iter(normalize_person(rows[0])))
    p2 = next(iter(normalize_person(rows[0])))
    assert p1.person_id == p2.person_id
    assert p1.person_id == uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_person:48")


def test_normalize_historical_mk_referenced_by_votes_cassette():
    """End-to-end: the historical MK referenced by CAST_VOTE edges
    gets a real ``hebrew_name`` when the People adapter runs. Prior
    to 2026-04-23 (when the manifest carried ``IsCurrent eq true``)
    this person was absent from the People cassette and the stub
    from ``civic_ingest_votes.upsert`` remained nameless forever.
    """
    rows = [r for r in parse_persons(_load_page()) if r["person_id_external"] == "405"]
    assert len(rows) == 1
    p = next(iter(normalize_person(rows[0])))
    assert p.hebrew_name == "בנימין אלון"
    assert p.canonical_name == "בנימין אלון"
    assert p.person_id == uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_person:405")
