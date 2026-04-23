"""Neo4j upsert for NormalizedBill bundles."""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedBill

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

BILL_TEMPLATE = UPSERT_ROOT / "bill_upsert.cypher"
SPONSORED_TEMPLATE = UPSERT_ROOT / "relationships" / "sponsored.cypher"


def upsert_bill(bill: NormalizedBill) -> dict:
    run_upsert(
        BILL_TEMPLATE,
        {
            "bill_id": str(bill.bill_id),
            "title": bill.title,
            "knesset_number": bill.knesset_number,
            "status": bill.status,
        },
    )
    for s in bill.sponsorships:
        run_upsert(
            SPONSORED_TEMPLATE,
            {
                "person_id": str(s.person_id),
                "bill_id": str(bill.bill_id),
            },
        )
    return {
        "bill_id": str(bill.bill_id),
        "sponsorships": len(bill.sponsorships),
    }
