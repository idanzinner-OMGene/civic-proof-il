"""Phase-2 + Phase-2.5 acceptance test.

End-to-end smoke test that exercises the full adapter pipeline against
the live docker-compose stack:

1. Stand up an :class:`civic_ingest.IngestRun`.
2. For each Phase-2 / Phase-2.5 adapter, replay the canonical fixture
   under ``tests/fixtures/phase2/cassettes/<adapter>/sample.{json,csv}``
   by monkey-patching the fetcher (no live HTTP — we exercise the
   archival, parse, normalize, and upsert paths deterministically).
3. Verify:
   * ``raw_fetch_objects`` accumulated one row per adapter.
   * ``ingest_runs.status`` transitioned to ``succeeded``.
   * Neo4j contains Person, Committee, Bill, VoteEvent, AttendanceEvent
     nodes plus the five Phase-2.5 edge lanes: CAST_VOTE, MEMBER_OF,
     HELD_OFFICE, MEMBER_OF_COMMITTEE, SPONSORED, ATTENDED.
   * Running the pipeline again doesn't produce duplicate rows or
     relationships (the ``content_sha256`` constraint + deterministic
     UUIDs keep it idempotent).

Marked ``@pytest.mark.integration`` so unit runs skip it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests/fixtures/phase2/cassettes"
LOOKUPS_ROOT = ROOT / "tests/fixtures/phase2/lookups"


def _have_live_stack() -> bool:
    """Return True iff the compose stack appears up."""

    try:
        from civic_clients.minio_client import ping as mping
        from civic_clients.neo4j import ping as nping
        from civic_clients.postgres import ping as pping
    except ImportError:
        return False
    return pping() and nping() and mping()


pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def live_stack():
    if not _have_live_stack():
        pytest.skip("live docker-compose stack not reachable")
    yield


@dataclass
class _StubFetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    fetched_at: datetime


def _stub_fetch_for(fixture_path: Path):
    content_type = (
        "text/csv" if fixture_path.suffix.lower() == ".csv" else "application/json"
    )

    def _fetch(url: str):
        return _StubFetchResult(
            url=url,
            status_code=200,
            content=fixture_path.read_bytes(),
            content_type=content_type,
            fetched_at=datetime.now(tz=timezone.utc),
        )

    return _fetch


def test_phase2_ingestion_roundtrip(live_stack):
    """Full happy path across the eight Phase-2 / Phase-2.5 adapters.

    Uses recorded real cassettes under ``tests/fixtures/phase2/cassettes/``.
    Phase-2.5 adds three new adapters (positions, bill_initiators,
    committee_memberships) that produce the five previously-missing
    relationship edges (MEMBER_OF, HELD_OFFICE, MEMBER_OF_COMMITTEE,
    SPONSORED, ATTENDED).
    """

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
    from civic_ingest_people import (
        normalize_person,
        parse_persons,
        upsert_person,
    )
    from civic_ingest_positions import (
        normalize_position,
        parse_positions,
        upsert_position,
    )
    from civic_ingest_sponsorships import (
        normalize_bill,
        parse_bills,
        upsert_bill,
    )
    from civic_ingest_votes import (
        normalize_vote,
        parse_votes,
        upsert_vote,
    )

    lookup = load_mk_individual_lookup(
        (LOOKUPS_ROOT / "mk_individual/sample.csv").read_bytes()
    )

    def _attendance_normalize(row):
        return normalize_attendance(row, lookup=lookup)

    def _committee_membership_normalize(row):
        return normalize_committee_membership(row, lookup=lookup)

    adapters = [
        ("people", "sample.json", "json", parse_odata_page, parse_persons, normalize_person, upsert_person),
        ("committees", "sample.json", "json", parse_odata_page, parse_committees, normalize_committee, upsert_committee),
        ("votes", "sample.csv", "csv", parse_csv_page, parse_votes, normalize_vote, upsert_vote),
        ("sponsorships", "sample.json", "json", parse_odata_page, parse_bills, normalize_bill, upsert_bill),
        ("attendance", "sample.csv", "csv", parse_csv_page, parse_attendance, _attendance_normalize, upsert_attendance),
        ("positions", "sample.json", "json", parse_odata_page, parse_positions, normalize_position, upsert_position),
        ("bill_initiators", "sample.json", "json", parse_odata_page, parse_bill_initiators, normalize_bill_initiator, upsert_bill_sponsorship),
        ("committee_memberships", "sample.csv", "csv", parse_csv_page, parse_committee_memberships, _committee_membership_normalize, upsert_committee_membership),
    ]

    archive_hashes: set[str] = set()
    with IngestRun(source_family="knesset") as run:
        for adapter, cassette, ext, page_parser, parse_fn, normalize_fn, upsert_fn in adapters:
            fixture = FIXTURE_ROOT / adapter / cassette
            fetch = _stub_fetch_for(fixture)

            def _archive(fr, *, _adapter=adapter, _ext=ext):
                rec = archive_payload(
                    source_family="knesset",
                    source_url=f"https://example.test/{_adapter}",
                    fetch_result=fr,
                    ingest_run_id=run.db_id,
                    source_tier=1,
                    extension_hint=_ext,
                    conn=run.connection,
                )
                archive_hashes.add(rec.content_sha256)
                return rec

            result = run_adapter(
                ingest_run=run,
                source_url=f"https://example.test/{adapter}",
                fetch=fetch,
                archive=_archive,
                parse=parse_fn,
                normalize=normalize_fn,
                upsert=upsert_fn,
                max_pages=1,
                page_parser=page_parser,
            )
            assert result.pages == 1, f"{adapter}: expected 1 page"
            assert result.rows_parsed >= 1, f"{adapter}: no rows parsed"

    assert len(archive_hashes) == len(adapters), (
        f"expected {len(adapters)} distinct content_sha256 archives across "
        f"adapters, got {len(archive_hashes)}"
    )

    from civic_clients.postgres import make_connection

    with make_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM raw_fetch_objects "
            " WHERE content_sha256 = ANY(%s)",
            (list(archive_hashes),),
        )
        raw_count = cur.fetchone()[0]
        assert raw_count == len(adapters), (
            f"expected {len(adapters)} raw_fetch_objects rows for this "
            f"run's hashes, got {raw_count}"
        )

        cur.execute(
            "SELECT status FROM ingest_runs WHERE run_id = %s",
            (str(run.run_id),),
        )
        status = cur.fetchone()[0]
        assert status == "succeeded", f"ingest_run should be succeeded, got {status}"

    from civic_clients.neo4j import make_driver

    driver = make_driver()
    with driver.session() as session:
        records = list(
            session.run(
                "MATCH (p:Person) "
                "WHERE p.external_ids IS NOT NULL "
                "  AND p.external_ids CONTAINS 'knesset_person_id' "
                "RETURN count(p) AS n"
            )
        )
        assert records and records[0]["n"] >= 2, (
            "expected at least 2 Person nodes from the people fixture"
        )

        # Phase-2 base: CAST_VOTE, AttendanceEvent, Committee, Bill.
        records = list(
            session.run(
                "MATCH (:Person)-[:CAST_VOTE]->(:VoteEvent) RETURN count(*) AS n"
            )
        )
        assert records[0]["n"] >= 1, "expected at least one CAST_VOTE edge"

        records = list(
            session.run("MATCH (:AttendanceEvent) RETURN count(*) AS n")
        )
        assert records[0]["n"] >= 1, "expected at least one AttendanceEvent node"

        records = list(session.run("MATCH (:Committee) RETURN count(*) AS n"))
        assert records[0]["n"] >= 1, "expected at least one Committee node"

        records = list(session.run("MATCH (:Bill) RETURN count(*) AS n"))
        assert records[0]["n"] >= 1, "expected at least one Bill node"

        # Phase-2.5 edge lanes.
        records = list(
            session.run(
                "MATCH (:Person)-[:MEMBER_OF]->(:Party) RETURN count(*) AS n"
            )
        )
        assert records[0]["n"] >= 1, (
            "expected at least one MEMBER_OF edge from the positions adapter"
        )

        records = list(
            session.run(
                "MATCH (:Person)-[:HELD_OFFICE]->(:Office) RETURN count(*) AS n"
            )
        )
        assert records[0]["n"] >= 1, (
            "expected at least one HELD_OFFICE edge from the positions adapter"
        )

        records = list(
            session.run(
                "MATCH (:Person)-[:MEMBER_OF_COMMITTEE]->(:Committee) "
                "RETURN count(*) AS n"
            )
        )
        assert records[0]["n"] >= 1, (
            "expected at least one MEMBER_OF_COMMITTEE edge from the "
            "committee_memberships adapter"
        )

        records = list(
            session.run(
                "MATCH (:Person)-[:SPONSORED]->(:Bill) RETURN count(*) AS n"
            )
        )
        assert records[0]["n"] >= 1, (
            "expected at least one SPONSORED edge from the bill_initiators adapter"
        )

        records = list(
            session.run(
                "MATCH (:Person)-[:ATTENDED]->(:AttendanceEvent) "
                "RETURN count(*) AS n"
            )
        )
        assert records[0]["n"] >= 1, (
            "expected at least one ATTENDED edge from the attendance adapter"
        )


def test_phase2_ingestion_is_idempotent(live_stack):
    """Re-running with the same fixtures must not duplicate Neo4j state."""

    from civic_ingest import IngestRun, run_adapter
    from civic_ingest_people import normalize_person, parse_persons, upsert_person

    fixture = FIXTURE_ROOT / "people" / "sample.json"

    def _count():
        from civic_clients.neo4j import make_driver

        with make_driver().session() as session:
            return list(
                session.run(
                    "MATCH (p:Person) "
                    "WHERE p.external_ids IS NOT NULL "
                    "  AND p.external_ids CONTAINS 'knesset_person_id' "
                    "RETURN count(p) AS n"
                )
            )[0]["n"]

    before = _count()
    with IngestRun(source_family="knesset") as run:
        run_adapter(
            ingest_run=run,
            source_url="https://example.test/people",
            fetch=_stub_fetch_for(fixture),
            archive=None,
            parse=parse_persons,
            normalize=normalize_person,
            upsert=upsert_person,
            max_pages=1,
        )
    after = _count()
    assert after == before, (
        f"person count changed: before={before} after={after} (upserts not idempotent)"
    )
