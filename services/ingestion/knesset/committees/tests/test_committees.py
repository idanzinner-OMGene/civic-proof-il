"""Unit tests for the committees adapter, pinned to the first row of the
recorded real cassette at ``tests/fixtures/phase2/cassettes/committees/``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import parse_odata_page
from civic_ingest_committees.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_committee,
)
from civic_ingest_committees.parse import parse_committees

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/committees/sample.json"
)


def _load():
    return parse_odata_page(SAMPLE.read_bytes())


def test_cassette_has_real_knesset_25_committees():
    page = _load()
    assert len(page.value) == 20
    assert page.value[0]["CommitteeID"] == 4185
    assert page.value[0]["Name"] == "הוועדה המסדרת"
    assert page.value[0]["KnessetNum"] == 25


def test_parse_yields_real_first_committee():
    rows = list(parse_committees(_load()))
    assert len(rows) == 20
    r0 = rows[0]
    assert r0["committee_id_external"] == "4185"
    assert r0["name_he"] == "הוועדה המסדרת"
    assert r0["knesset_number"] == 25
    assert r0["committee_type"] == "ועדה מיוחדת"


def test_normalize_produces_committee_without_embedded_memberships():
    row = next(iter(parse_committees(_load())))
    bundles = list(normalize_committee(row))
    assert len(bundles) == 1
    c = bundles[0]
    assert c.hebrew_name == "הוועדה המסדרת"
    assert c.canonical_name == "הוועדה המסדרת"
    assert c.knesset_number == 25
    assert c.committee_type == "ועדה מיוחדת"
    assert c.memberships == ()  # real OData has no embedded members
    assert c.committee_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_committee:4185"
    )
