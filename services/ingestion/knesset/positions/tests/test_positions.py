"""Unit tests for the positions adapter, pinned to the real recorded
cassette at ``tests/fixtures/phase2/cassettes/positions/sample.json``.

Per ``.cursor/rules/real-data-tests.mdc``, every assertion binds to an
ID / string that came off the live Knesset OData feed.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import parse_odata_page
from civic_ingest_positions.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_position,
)
from civic_ingest_positions.parse import parse_positions

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/positions/sample.json"
)


def _load():
    return parse_odata_page(SAMPLE.read_bytes())


def test_cassette_is_knesset_25():
    page = _load()
    assert len(page.value) == 100
    first = page.value[0]
    assert first["PersonToPositionID"] == 30177
    assert first["PersonID"] == 30749
    assert first["KnessetNum"] == 25
    assert first["PositionID"] == 54
    assert first["FactionID"] == 1095


def test_parse_yields_first_row_keys():
    rows = list(parse_positions(_load()))
    assert len(rows) == 100
    r0 = rows[0]
    assert r0["person_to_position_id_external"] == "30177"
    assert r0["person_id_external"] == "30749"
    assert r0["position_id"] == 54
    assert r0["faction_id_external"] == "1095"
    assert r0["start_date"] == "2022-11-15T00:00:00"
    assert r0["finish_date"] is None


def test_committee_lane_is_empty_across_entire_cassette():
    """Documents the real-data shape: ``KNS_PersonToPosition`` declares
    ``CommitteeID``/``CommitteeName`` columns but 0/100 rows in the
    recorded slice (and 0/11,090 upstream) have them populated. If
    this assertion ever flips, committee memberships have started
    flowing through this table and the adapter must start emitting
    MEMBER_OF_COMMITTEE edges."""
    rows = list(parse_positions(_load()))
    assert all(r["committee_id_external"] is None for r in rows)
    assert all(r["committee_name"] is None for r in rows)


def test_normalize_first_row_emits_both_lanes():
    row = next(iter(parse_positions(_load())))
    bundles = list(normalize_position(row))
    assert len(bundles) == 1
    b = bundles[0]

    assert b.person_id == uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_person:30749")

    assert b.party is not None
    assert b.party.party_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_party:1095"
    )
    assert "שס" in b.party.party_name or "הספרדים" in b.party.party_name
    assert b.party.valid_from == "2022-11-15T00:00:00"
    assert b.party.valid_to is None

    assert b.office is not None
    assert b.office.office_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_office:54:-"
    )
    assert b.office.office_type == "mk"
    assert b.office.scope == "national"
    assert b.office.valid_from == "2022-11-15T00:00:00"


def test_office_id_uses_composite_key_when_gov_ministry_present():
    synthetic = {
        "person_to_position_id_external": "99999",
        "person_id_external": "1",
        "position_id": 49,
        "faction_id_external": None,
        "faction_name": None,
        "committee_id_external": None,
        "committee_name": None,
        "gov_ministry_id": "559",
        "gov_ministry_name": "משרד ראש הממשלה",
        "duty_desc": "שר",
        "start_date": "2022-11-15T00:00:00",
        "finish_date": None,
        "knesset_num": 25,
        "is_current": False,
    }
    bundle = next(iter(normalize_position(synthetic)))
    assert bundle.office is not None
    assert bundle.office.office_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_office:49:559"
    )
    assert bundle.office.canonical_name == "משרד ראש הממשלה"
    assert bundle.office.office_type == "minister"


def test_normalize_skips_rows_without_start_date():
    synthetic = {
        "person_to_position_id_external": "99998",
        "person_id_external": "1",
        "position_id": 54,
        "faction_id_external": None,
        "faction_name": None,
        "committee_id_external": None,
        "committee_name": None,
        "gov_ministry_id": None,
        "gov_ministry_name": None,
        "duty_desc": None,
        "start_date": None,
        "finish_date": None,
        "knesset_num": 25,
        "is_current": False,
    }
    assert list(normalize_position(synthetic)) == []


def test_normalize_deputy_speaker_row_has_valid_to():
    for row in parse_positions(_load()):
        if row["position_id"] == 48:
            bundle = next(iter(normalize_position(row)))
            assert bundle.office is not None
            assert bundle.office.valid_to == "2023-01-02T00:00:00"
            return
    raise AssertionError("expected a PositionID=48 row in the cassette")
