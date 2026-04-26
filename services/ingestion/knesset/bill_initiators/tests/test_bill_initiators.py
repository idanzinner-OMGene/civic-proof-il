"""Unit tests for the bill_initiators adapter, pinned to the real
recorded cassette at
``tests/fixtures/phase2/cassettes/bill_initiators/sample.json``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest import parse_odata_page
from civic_ingest_bill_initiators.normalize import (
    PHASE2_UUID_NAMESPACE,
    normalize_bill_initiator,
)
from civic_ingest_bill_initiators.parse import parse_bill_initiators

SAMPLE = (
    Path(__file__).resolve().parents[5]
    / "tests/fixtures/phase2/cassettes/bill_initiators/sample.json"
)


def _load():
    return parse_odata_page(SAMPLE.read_bytes())


def test_cassette_first_row_is_recent_initiator():
    page = _load()
    assert len(page.value) == 100
    first = page.value[0]
    assert first["BillInitiatorID"] == 229537
    assert first["BillID"] == 81589
    assert first["PersonID"] == 1049
    assert first["IsInitiator"] is True


def test_parse_drops_non_initiator_rows():
    rows = list(parse_bill_initiators(_load()))
    assert len(rows) == 76
    assert all(r["bill_id_external"] for r in rows)
    r0 = rows[0]
    assert r0["bill_initiator_id_external"] == "229537"
    assert r0["bill_id_external"] == "81589"
    assert r0["person_id_external"] == "1049"
    assert r0["ordinal"] == 2


def test_normalize_emits_deterministic_uuids():
    row = next(iter(parse_bill_initiators(_load())))
    sponsorships = list(normalize_bill_initiator(row))
    assert len(sponsorships) == 1
    s = sponsorships[0]

    assert s.bill_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_bill:81589"
    )
    assert s.person_id == uuid.uuid5(
        PHASE2_UUID_NAMESPACE, "knesset_person:1049"
    )
    assert s.ordinal == 2


def test_normalize_uses_same_uuid_namespace_as_sponsorships_adapter():
    from civic_ingest_sponsorships.normalize import (
        PHASE2_UUID_NAMESPACE as SPONSORSHIPS_NS,
    )

    assert PHASE2_UUID_NAMESPACE == SPONSORSHIPS_NS


def test_normalize_uses_same_uuid_namespace_as_people_adapter():
    from civic_ingest_people.normalize import (
        PHASE2_UUID_NAMESPACE as PEOPLE_NS,
    )

    assert PHASE2_UUID_NAMESPACE == PEOPLE_NS
