"""Unit tests for the sponsorships (bills) adapter, pinned to the first
row of the real recorded cassette at
``tests/fixtures/phase2/cassettes/sponsorships/sample.json``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import parse_odata_page
from civic_ingest_sponsorships.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_bill,
)
from civic_ingest_sponsorships.parse import parse_bills

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/sponsorships/sample.json"
)


def _load():
    return parse_odata_page(SAMPLE.read_bytes())


def test_cassette_has_real_knesset_25_bills():
    page = _load()
    assert len(page.value) == 20
    first = page.value[0]
    assert first["BillID"] == 1038990
    assert first["KnessetNum"] == 25
    assert "הצעת חוק הירושה" in first["Name"]


def test_parse_yields_real_first_bill():
    rows = list(parse_bills(_load()))
    assert len(rows) == 20
    r0 = rows[0]
    assert r0["bill_id_external"] == "1038990"
    assert r0["knesset_number"] == 25
    assert r0["sub_type"] == "ממשלתית"
    assert r0["title_he"].startswith("הצעת חוק הירושה")


def test_normalize_emits_bill_without_embedded_sponsorships():
    row = next(iter(parse_bills(_load())))
    bills = list(normalize_bill(row))
    assert len(bills) == 1
    bill = bills[0]
    assert bill.bill_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_bill:1038990"
    )
    assert bill.title.startswith("הצעת חוק הירושה")
    assert bill.knesset_number == 25
    assert bill.sponsorships == ()
    assert bill.sub_type == "ממשלתית"
