"""Unit tests for the committee_memberships adapter, pinned to the real
recorded cassette at
``tests/fixtures/phase2/cassettes/committee_memberships/sample.csv`` and
the real ``mk_individual`` lookup at
``tests/fixtures/phase2/lookups/mk_individual/sample.csv``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import load_mk_individual_lookup, parse_csv_page
from civic_ingest_committee_memberships.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_committee_membership,
)
from civic_ingest_committee_memberships.parse import (
    parse_committee_memberships,
)

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/committee_memberships/sample.csv"
)


def _load():
    return parse_csv_page(SAMPLE.read_bytes())


def _lookup():
    return load_mk_individual_lookup()


def test_cassette_first_row_is_knesset_25():
    page = _load()
    assert len(page.value) == 100
    first = page.value[0]
    assert first["mk_individual_id"] == "30775"
    assert first["committee_id"] == "4282"
    assert first["knesset"] == "25"
    assert first["start_date"] == "2026-03-25"


def test_parse_emits_expected_keys():
    rows = list(parse_committee_memberships(_load()))
    assert len(rows) == 100
    r0 = rows[0]
    assert r0["mk_individual_id"] == "30775"
    assert r0["committee_id_external"] == "4282"
    assert r0["position_name"] == 'מ"מ חבר ועדה'
    assert r0["finish_date"] is None


def test_lookup_loads_full_dimension_table():
    lookup = _lookup()
    # The recorded lookup file has 1184 rows.
    assert len(lookup) >= 1000
    assert "30775" in lookup
    assert lookup.resolve("30775") == "30775"
    assert lookup.resolve("103") == "563"


def test_normalize_resolves_mk_individual_to_person_id():
    lookup = _lookup()
    row = next(iter(parse_committee_memberships(_load())))
    memberships = list(normalize_committee_membership(row, lookup=lookup))
    assert len(memberships) == 1
    m = memberships[0]

    assert m.person_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_person:30775"
    )
    assert m.committee_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_committee:4282"
    )
    assert m.valid_from == "2026-03-25T00:00:00"
    assert m.valid_to is None
    assert m.knesset == 25
    assert m.mk_individual_id == "30775"


def test_normalize_second_row_joins_to_different_person_id():
    lookup = _lookup()
    rows = list(parse_committee_memberships(_load()))
    memberships = list(
        normalize_committee_membership(rows[1], lookup=lookup)
    )
    assert len(memberships) == 1
    m = memberships[0]
    assert m.person_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_person:563"
    )


def test_normalize_skips_rows_whose_mk_individual_cannot_be_resolved():
    lookup = _lookup()
    synthetic = {
        "mk_individual_id": "9999999",
        "committee_id_external": "4282",
        "committee_name": "x",
        "position_id": "42",
        "position_name": "חבר ועדה",
        "start_date": "2026-03-24",
        "finish_date": None,
        "knesset": "25",
    }
    assert list(normalize_committee_membership(synthetic, lookup=lookup)) == []


def test_full_cassette_resolves_against_lookup_without_drops():
    """Full-corpus real-data check: every row in the cassette must
    resolve through the real mk_individual lookup. If this ever fails,
    either the cassette needs re-recording or the lookup does."""
    lookup = _lookup()
    rows = list(parse_committee_memberships(_load()))
    memberships = [
        m
        for row in rows
        for m in normalize_committee_membership(row, lookup=lookup)
    ]
    assert len(memberships) == len(rows)


def test_namespace_is_the_shared_phase2_namespace():
    from civic_ingest_people.normalize import (
        PHASE2_UUID_NAMESPACE as PEOPLE_NS,
    )
    from civic_ingest_committees.normalize import (
        PHASE2_UUID_NAMESPACE as COMMITTEES_NS,
    )

    assert PHASE2_UUID_NAMESPACE == PEOPLE_NS == COMMITTEES_NS
