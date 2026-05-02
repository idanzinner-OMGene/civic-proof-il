#!/usr/bin/env python3
"""Seed the live stack with a minimal representative dataset from cassettes.

Replays all eight Phase-2/2.5 ingestion adapters against the recorded cassettes
under ``tests/fixtures/phase2/cassettes/``.  No internet access required — the
fetcher is swapped out for a stub that returns the cassette bytes.

Usage::

    uv run python scripts/seed_demo.py

Prerequisites: ``make up`` and ``make migrate`` must have run first.

What it loads:
  - ~50 Person nodes (KNS_Person sample)
  - ~89 Committee nodes (Knesset-25 KNS_Committee sample)
  - Party, Office, MEMBER_OF, HELD_OFFICE edges (KNS_PersonToPosition sample)
  - MEMBER_OF_COMMITTEE edges (oknesset committee_memberships sample)
  - Bill + SPONSORED edges (KNS_Bill + KNS_BillInitiator samples)
  - VoteEvent + CAST_VOTE edges (oknesset votes sample)
  - AttendanceEvent + ATTENDED edges (oknesset attendance sample)

Re-running is idempotent: content-addressed deduplication in archive_payload and
deterministic UUID5 keys in Neo4j ensure no duplicates on repeat runs.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASSETTE_ROOT = ROOT / "tests/fixtures/phase2/cassettes"
LOOKUPS_ROOT = ROOT / "tests/fixtures/phase2/lookups"

sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "clients" / "src"))


def _check_stack() -> bool:
    try:
        from civic_clients.minio_client import ping as mping
        from civic_clients.neo4j import ping as nping
        from civic_clients.opensearch import ping as oping
        from civic_clients.postgres import ping as pping
    except ImportError as exc:
        print(f"civic_clients not importable: {exc}", file=sys.stderr)
        return False
    ok = pping() and nping() and mping() and oping()
    if not ok:
        print(
            "One or more backing stores unreachable. Run `make up` and `make migrate` first.",
            file=sys.stderr,
        )
    return ok


@dataclass
class _StubFetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    fetched_at: datetime


def _stub_fetch_for(fixture_path: Path):
    content_type = "text/csv" if fixture_path.suffix.lower() == ".csv" else "application/json"

    def _fetch(url: str) -> _StubFetchResult:
        return _StubFetchResult(
            url=url,
            status_code=200,
            content=fixture_path.read_bytes(),
            content_type=content_type,
            fetched_at=datetime.now(tz=UTC),
        )

    return _fetch


def main() -> int:
    print("==> civic-proof-il seed-demo")
    print("    Replaying cassettes → live stack (no internet required)")
    print()

    print("==> Checking stack readiness...")
    if not _check_stack():
        return 1
    print("    [ok] all backing stores reachable")
    print()

    from civic_archival import archive_payload
    from civic_ingest import (
        IngestRun,
        load_mk_individual_lookup,
        parse_csv_page,
        parse_odata_page,
        run_adapter,
    )
    from civic_ingest_attendance import (
        normalize_attendance,
        parse_attendance,
        upsert_attendance,
    )
    from civic_ingest_bill_initiators import (
        normalize_bill_initiator,
        parse_bill_initiators,
        upsert_bill_sponsorship,
    )
    from civic_ingest_committee_memberships import (
        normalize_committee_membership,
        parse_committee_memberships,
        upsert_committee_membership,
    )
    from civic_ingest_committees import (
        normalize_committee,
        parse_committees,
        upsert_committee,
    )
    from civic_ingest_people import normalize_person, parse_persons, upsert_person
    from civic_ingest_positions import normalize_position, parse_positions, upsert_position
    from civic_ingest_sponsorships import normalize_bill, parse_bills, upsert_bill
    from civic_ingest_votes import normalize_vote, parse_votes, upsert_vote

    lookup = load_mk_individual_lookup((LOOKUPS_ROOT / "mk_individual/sample.csv").read_bytes())

    def _attendance_normalize(row):
        return normalize_attendance(row, lookup=lookup)

    def _committee_membership_normalize(row):
        return normalize_committee_membership(row, lookup=lookup)

    adapters = [
        (
            "people",
            "sample.json",
            "json",
            parse_odata_page,
            parse_persons,
            normalize_person,
            upsert_person,
        ),
        (
            "committees",
            "sample.json",
            "json",
            parse_odata_page,
            parse_committees,
            normalize_committee,
            upsert_committee,
        ),
        (
            "positions",
            "sample.json",
            "json",
            parse_odata_page,
            parse_positions,
            normalize_position,
            upsert_position,
        ),
        (
            "committee_memberships",
            "sample.csv",
            "csv",
            parse_csv_page,
            parse_committee_memberships,
            _committee_membership_normalize,
            upsert_committee_membership,
        ),
        (
            "sponsorships",
            "sample.json",
            "json",
            parse_odata_page,
            parse_bills,
            normalize_bill,
            upsert_bill,
        ),
        (
            "bill_initiators",
            "sample.json",
            "json",
            parse_odata_page,
            parse_bill_initiators,
            normalize_bill_initiator,
            upsert_bill_sponsorship,
        ),
        (
            "votes",
            "sample.csv",
            "csv",
            parse_csv_page,
            parse_votes,
            normalize_vote,
            upsert_vote,
        ),
        (
            "attendance",
            "sample.csv",
            "csv",
            parse_csv_page,
            parse_attendance,
            _attendance_normalize,
            upsert_attendance,
        ),
    ]

    print("==> Loading cassette data into live stack...")
    print()

    with IngestRun(source_family="knesset") as run:
        total_upserted = 0
        for adapter, cassette, ext, page_parser, parse_fn, normalize_fn, upsert_fn in adapters:
            fixture = CASSETTE_ROOT / adapter / cassette
            if not fixture.is_file():
                print(f"    [skip] {adapter}: cassette not found at {fixture}")
                continue

            fetch = _stub_fetch_for(fixture)

            def _archive(fr, *, _adapter=adapter, _ext=ext):
                return archive_payload(
                    source_family="knesset",
                    source_url=f"https://seed-demo.test/{_adapter}",
                    fetch_result=fr,
                    ingest_run_id=run.db_id,
                    source_tier=1,
                    extension_hint=_ext,
                    conn=run.connection,
                )

            result = run_adapter(
                ingest_run=run,
                adapter=adapter,
                source_url=f"https://seed-demo.test/{adapter}",
                fetch=fetch,
                archive=_archive,
                parse=parse_fn,
                normalize=normalize_fn,
                upsert=upsert_fn,
                max_pages=1,
                page_parser=page_parser,
            )
            print(
                f"    [ok] {adapter:<25} "
                f"rows_parsed={result.rows_parsed:>4}  "
                f"rows_upserted={result.rows_upserted:>4}"
            )
            total_upserted += result.rows_upserted

    print()
    print(f"==> seed-demo complete — {total_upserted} total rows upserted (idempotent)")
    print()
    print("    Try verifying a claim:")
    print("      curl -s -X POST http://localhost:8000/claims/verify \\")
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"statement": "ישראל כץ כיהן כחבר כנסת", "language": "he"}\'')
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
