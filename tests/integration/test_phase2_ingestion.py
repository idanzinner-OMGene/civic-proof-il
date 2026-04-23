"""Phase-2 acceptance test.

End-to-end smoke test that exercises the full adapter pipeline against
the live docker-compose stack:

1. Stand up an :class:`civic_ingest.IngestRun`.
2. For each of the five Phase-2 adapters, replay the canonical fixture
   from ``tests/fixtures/phase2/cassettes/<adapter>/sample.json`` by
   monkey-patching the fetcher (no live HTTP — we exercise the archival,
   parse, normalize, and upsert paths deterministically).
3. Verify:
   * ``raw_fetch_objects`` accumulated five rows (one per adapter).
   * ``ingest_runs.status`` transitioned to ``succeeded``.
   * Neo4j contains Person, Committee, Bill, VoteEvent, AttendanceEvent
     nodes plus CAST_VOTE edges (party/office/sponsorship joins are
     Phase-3 and intentionally absent from Phase-2 real-data cassettes).
   * Running the pipeline again doesn't produce duplicate rows or
     relationships (the ``content_sha256`` constraint + deterministic
     UUIDs keep it idempotent).

Marked ``@pytest.mark.integration`` so unit runs skip it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests/fixtures/phase2/cassettes"


def _have_live_stack() -> bool:
    """Return True iff the compose stack appears up.

    Same gate as ``test_phase1_persistence.py`` — we hard-skip the
    whole module when any service is unreachable so we don't emit
    flaky half-wrote state.
    """

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
    """Full happy path across all five adapters.

    Uses the recorded real cassettes under ``tests/fixtures/phase2/cassettes/``.
    Real Knesset OData is more normalized than the old synthetic fixtures:
    ``KNS_Person`` has no embedded party/office, ``KNS_Bill`` has no
    embedded initiators, ``KNS_CommitteeSession`` has no embedded
    attendees. Those joins are Phase-3. This test therefore asserts
    Phase-2 outputs only (foundational nodes + CAST_VOTE edges from the
    oknesset CSV).
    """

    from civic_archival import archive_payload
    from civic_ingest import IngestRun, parse_csv_page, parse_odata_page, run_adapter
    from civic_ingest_attendance import normalize_attendance, parse_attendance, upsert_attendance
    from civic_ingest_committees import normalize_committee, parse_committees, upsert_committee
    from civic_ingest_people import normalize_person, parse_persons, upsert_person
    from civic_ingest_sponsorships import normalize_bill, parse_bills, upsert_bill
    from civic_ingest_votes import normalize_vote, parse_votes, upsert_vote

    adapters = [
        ("people", "sample.json", "json", parse_odata_page, parse_persons, normalize_person, upsert_person),
        ("committees", "sample.json", "json", parse_odata_page, parse_committees, normalize_committee, upsert_committee),
        ("votes", "sample.csv", "csv", parse_csv_page, parse_votes, normalize_vote, upsert_vote),
        ("sponsorships", "sample.json", "json", parse_odata_page, parse_bills, normalize_bill, upsert_bill),
        ("attendance", "sample.json", "json", parse_odata_page, parse_attendance, normalize_attendance, upsert_attendance),
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

    assert len(archive_hashes) == 5, (
        f"expected 5 distinct content_sha256 archives across adapters, "
        f"got {len(archive_hashes)}"
    )

    # Verify persistence side effects. ``raw_fetch_objects`` is keyed by
    # ``content_sha256`` (globally dedup'd), so on re-runs the row may
    # belong to an earlier ingest_run_id. We assert presence-of-hash
    # rather than count-by-run so the test is rerun-safe.
    from civic_clients.postgres import make_connection

    with make_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM raw_fetch_objects "
            " WHERE content_sha256 = ANY(%s)",
            (list(archive_hashes),),
        )
        raw_count = cur.fetchone()[0]
        assert raw_count == 5, (
            f"expected 5 raw_fetch_objects rows for this run's hashes, "
            f"got {raw_count}"
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

        # Phase-2 foundational nodes only. Party/Office/Bill-sponsorship
        # relationships live in Phase-3 (they require joining
        # KNS_PersonToPosition / KNS_BillInitiator, which aren't in any
        # Phase-2 cassette). CAST_VOTE edges come from the oknesset
        # vote CSV; AttendanceEvents come from KNS_CommitteeSession.
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
