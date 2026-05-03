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
    NormalizedPositionTerm,
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


# ---- V2 PositionTerm tests ------------------------------------------------


def test_normalize_first_row_emits_position_term():
    """First real cassette row (PersonToPositionID=30177, PositionID=54 MK)
    must produce a PositionTerm with expected field values."""
    row = next(iter(parse_positions(_load())))
    bundle = next(iter(normalize_position(row)))

    assert bundle.position_term is not None
    pt = bundle.position_term
    assert isinstance(pt, NormalizedPositionTerm)

    # Deterministic ID from the external PersonToPositionID
    expected_id = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_position_term:30177")
    assert pt.position_term_id == expected_id

    # Person / office IDs must match the bundle's other fields
    assert pt.person_id == bundle.person_id
    assert bundle.office is not None
    assert pt.office_id == bundle.office.office_id

    # Dates mirror the office lane
    assert pt.valid_from == "2022-11-15T00:00:00"
    assert pt.valid_to is None

    # MK role is appointed by the Knesset, not the government
    assert pt.appointing_body == "knesset"
    assert pt.is_acting is False


def test_position_term_id_is_deterministic():
    """Same upstream row always produces the same position_term_id UUID."""
    rows = list(parse_positions(_load()))
    first_row = rows[0]

    bundle_a = next(iter(normalize_position(first_row)))
    bundle_b = next(iter(normalize_position(first_row)))

    assert bundle_a.position_term is not None
    assert bundle_b.position_term is not None
    assert bundle_a.position_term.position_term_id == bundle_b.position_term.position_term_id


def test_every_office_row_has_position_term():
    """Every row in the cassette that has an office lane must also have a
    position_term — the two are always emitted together."""
    rows = list(parse_positions(_load()))
    for row in rows:
        for bundle in normalize_position(row):
            if bundle.office is not None:
                assert bundle.position_term is not None, (
                    f"missing position_term for person_to_position_id "
                    f"{bundle.person_to_position_id_external}"
                )


def test_minister_row_appointing_body_is_government():
    """PositionID=49 (minister) must set appointing_body='government'."""
    synthetic = {
        "person_to_position_id_external": "99997",
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
        "is_current": True,
    }
    bundle = next(iter(normalize_position(synthetic)))
    assert bundle.position_term is not None
    assert bundle.position_term.appointing_body == "government"


def test_prime_minister_appointing_body_is_government():
    """PositionID=30 (prime_minister) must also be 'government'."""
    synthetic = {
        "person_to_position_id_external": "99996",
        "person_id_external": "1",
        "position_id": 30,
        "faction_id_external": None,
        "faction_name": None,
        "committee_id_external": None,
        "committee_name": None,
        "gov_ministry_id": "559",
        "gov_ministry_name": "משרד ראש הממשלה",
        "duty_desc": "ראש ממשלה",
        "start_date": "2022-11-15T00:00:00",
        "finish_date": None,
        "knesset_num": 25,
        "is_current": True,
    }
    bundle = next(iter(normalize_position(synthetic)))
    assert bundle.position_term is not None
    assert bundle.position_term.appointing_body == "government"


def test_pure_party_row_has_no_position_term():
    """A row with only a faction lane (no PositionID) must not produce a
    position_term.  Knesset OData always has PositionID, so this is a
    synthetic edge-case guard for future data shape changes."""
    synthetic = {
        "person_to_position_id_external": "99995",
        "person_id_external": "1",
        "position_id": None,
        "faction_id_external": "1095",
        "faction_name": "שס",
        "committee_id_external": None,
        "committee_name": None,
        "gov_ministry_id": None,
        "gov_ministry_name": None,
        "duty_desc": None,
        "start_date": "2022-11-15T00:00:00",
        "finish_date": None,
        "knesset_num": 25,
        "is_current": True,
    }
    bundle = next(iter(normalize_position(synthetic)))
    assert bundle.office is None
    assert bundle.position_term is None


def test_position_term_ids_are_unique_across_cassette():
    """Every row in the cassette must produce a distinct position_term_id
    (keyed by PersonToPositionID, which is unique upstream)."""
    ids: list[uuid.UUID] = []
    for row in parse_positions(_load()):
        for bundle in normalize_position(row):
            if bundle.position_term is not None:
                ids.append(bundle.position_term.position_term_id)
    assert len(ids) == len(set(ids)), "duplicate position_term_ids detected"
