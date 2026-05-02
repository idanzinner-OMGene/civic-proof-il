#!/usr/bin/env python3
"""Enrich VoteEvent nodes with bill_id and create ABOUT_BILL edges.

The votes CSV (oknesset) lists one row per MK per vote but does not carry a
BillID.  The authoritative bill link lives in the KNS_Vote OData endpoint,
which maps VoteID → BillID.

This script:
1. Fetches KNS_Vote OData (VoteID, BillID, VoteDate, VoteType) — all pages.
2. For each row where BillID is not null:
   a. Computes deterministic UUIDs for vote_event_id and bill_id.
   b. If the VoteEvent node exists in Neo4j, sets bill_id on it.
   c. If the Bill node also exists, MERGEs the (:VoteEvent)-[:ABOUT_BILL]->(:Bill) edge.
3. Rows whose VoteEvent or Bill node doesn't exist are silently skipped (the
   votes or sponsorships adapter wasn't run for that Knesset term).

Usage::

    uv run python scripts/enrich_vote_bills.py [--dry-run] [--max-pages N]

Prerequisites: make up (Neo4j + Postgres) with at least the votes and
sponsorships adapters having been run.

Idempotent: re-running sets the same properties and MERGEs the same edges.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "clients" / "src"))

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")
KNS_VOTE_URL = (
    "https://knesset.gov.il/OdataV4/ParliamentInfo.svc/KNS_Vote"
    "?$select=VoteID,BillID,StartDate,VoteType"
    "&$orderby=VoteID desc"
)
UPSERT_TEMPLATE = (
    ROOT / "infra" / "neo4j" / "upserts" / "relationships" / "vote_event_about_bill.cypher"
)


def _ext_uuid(kind: str, ext_id: str) -> str:
    return str(uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}"))


def _parse_odata_pages(fetcher, url: str, max_pages: int | None):
    """Yield individual record dicts from all OData pages."""
    from civic_ingest import iter_odata_pages, parse_odata_page

    for page_num, page in enumerate(iter_odata_pages(fetcher.fetch, url), start=1):
        parsed = parse_odata_page(page)
        yield from parsed.value
        if max_pages and page_num >= max_pages:
            break


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich VoteEvent nodes with ABOUT_BILL edges")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, skip Neo4j writes")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit OData page count")
    args = parser.parse_args(argv)

    if not UPSERT_TEMPLATE.is_file():
        print(f"Upsert template not found: {UPSERT_TEMPLATE}", file=sys.stderr)
        return 1

    cypher = UPSERT_TEMPLATE.read_text(encoding="utf-8")

    from civic_archival import Fetcher
    from civic_clients.neo4j import make_driver
    from civic_clients.neo4j import ping as neo4j_ping

    if not neo4j_ping():
        print("Neo4j not reachable. Run `make up` first.", file=sys.stderr)
        return 1

    fetcher = Fetcher()
    driver = make_driver()

    n_processed = 0
    n_linked = 0
    n_missing = 0

    print(f"{'[dry-run] ' if args.dry_run else ''}Fetching KNS_Vote OData…")

    try:
        with driver.session() as session:
            for row in _parse_odata_pages(fetcher, KNS_VOTE_URL, args.max_pages):
                vote_id = row.get("VoteID")
                bill_id_ext = row.get("BillID")
                if not vote_id or not bill_id_ext:
                    continue

                vote_event_id = _ext_uuid("knesset_vote", str(vote_id))
                bill_id = _ext_uuid("knesset_bill", str(bill_id_ext))
                occurred_at = row.get("StartDate")
                vote_type = row.get("VoteType")

                n_processed += 1

                if args.dry_run:
                    n_linked += 1
                    continue

                result = list(session.run(
                    cypher,
                    vote_event_id=vote_event_id,
                    bill_id=bill_id,
                    occurred_at=occurred_at,
                    vote_type=vote_type,
                ))
                if result:
                    n_linked += 1
                else:
                    n_missing += 1

                if n_processed % 1000 == 0:
                    print(
                        f"  …{n_processed} rows processed, "
                        f"{n_linked} linked, {n_missing} skipped"
                    )
    finally:
        driver.close()

    print(
        f"Done — {n_processed} rows processed, "
        f"{n_linked} ABOUT_BILL edges upserted, "
        f"{n_missing} skipped (VoteEvent or Bill not in graph)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
