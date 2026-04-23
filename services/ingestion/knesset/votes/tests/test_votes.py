"""Unit tests for the votes adapter, pinned to the first row of the real
per-MK votes cassette at ``tests/fixtures/phase2/cassettes/votes/sample.csv``.

The cassette is a truncated prefix of the hasadna/OpenKnesset mirror of
``vote_rslts_kmmbr_shadow.csv`` — the Knesset's own per-MK votes feed
is behind a bot challenge, so the mirror is the realistic data source.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import parse_csv_page
from civic_ingest_votes.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_vote,
)
from civic_ingest_votes.parse import parse_votes

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/votes/sample.csv"
)


def _load():
    return parse_csv_page(SAMPLE.read_bytes())


def test_cassette_has_real_per_mk_vote_rows():
    page = _load()
    assert page.value, "cassette should have at least one row"
    header = list(page.value[0].keys())
    assert header[0] == "vote_id"
    assert "kmmbr_id" in header
    assert "vote_result" in header
    first = page.value[0]
    assert first["vote_id"] == "94"
    assert first["kmmbr_name"] == "בנימין אלון"
    assert first["vote_result"] == "1"


def test_parse_yields_real_first_row():
    rows = list(parse_votes(_load()))
    r0 = rows[0]
    assert r0["vote_id_external"] == "94"
    assert r0["person_id_external"] == "405"
    assert r0["vote_result"] == 1
    assert r0["knesset_number"] == 16
    assert r0["faction_name_he"] == "האיחוד הלאומי-ישראל ביתנו"


def test_normalize_maps_vote_result_code_and_pins_uuids():
    row = next(iter(parse_votes(_load())))
    events = list(normalize_vote(row))
    assert len(events) == 1
    ev = events[0]
    assert ev.vote_event_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_vote:94"
    )
    assert ev.bill_id is None
    assert ev.knesset_number == 16
    assert len(ev.cast_votes) == 1
    cv = ev.cast_votes[0]
    assert cv.value == "for"
    assert cv.person_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_person:405"
    )


def test_normalize_drops_cast_vote_for_unknown_result_code():
    row = {
        "vote_id_external": "94",
        "person_id_external": "405",
        "vote_result": 0,  # absent
    }
    events = list(normalize_vote(row))
    assert len(events) == 1
    assert events[0].cast_votes == ()


def test_parse_drops_rows_missing_keys():
    page = parse_csv_page(b"vote_id,kmmbr_id,vote_result,knesset_num\n,100,1,25\n")
    assert list(parse_votes(page)) == []
