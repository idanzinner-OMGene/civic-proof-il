"""Neo4j upsert for :class:`NormalizedBillSponsorship`.

Three ``run_upsert`` calls per sponsorship:

1. Person stub MERGE — the people adapter may not yet have ingested
   this historical ``PersonID``.
2. Bill stub MERGE — the sponsorships adapter ingests bill metadata,
   but bill_initiators may see BillID values that precede the
   sponsorships cassette slice.
3. SPONSORED edge MERGE.
"""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedBillSponsorship

__all__ = ["upsert_bill_sponsorship"]

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

PERSON_TEMPLATE = UPSERT_ROOT / "person_upsert.cypher"
BILL_TEMPLATE = UPSERT_ROOT / "bill_upsert.cypher"
SPONSORED_TEMPLATE = UPSERT_ROOT / "relationships" / "sponsored.cypher"


def upsert_bill_sponsorship(sponsorship: NormalizedBillSponsorship) -> dict:
    person_id_str = str(sponsorship.person_id)
    bill_id_str = str(sponsorship.bill_id)

    run_upsert(
        PERSON_TEMPLATE,
        {
            "person_id": person_id_str,
            "canonical_name": None,
            "hebrew_name": None,
            "english_name": None,
            "external_ids": None,
            "source_tier": 1,
        },
    )
    run_upsert(
        BILL_TEMPLATE,
        {
            "bill_id": bill_id_str,
            "title": None,
            "knesset_number": None,
            "status": None,
        },
    )
    run_upsert(
        SPONSORED_TEMPLATE,
        {
            "person_id": person_id_str,
            "bill_id": bill_id_str,
        },
    )
    return {
        "person_id": person_id_str,
        "bill_id": bill_id_str,
        "ordinal": sponsorship.ordinal,
    }
