"""Phase-1 acceptance test (plan line 93).

End-to-end round-trip: validate the Phase-1 fixtures via Pydantic, persist
a ``Person`` / ``Office`` / ``MembershipTerm`` / ``SourceDocument`` /
``EvidenceSpan`` / ``AtomicClaim`` / ``Verdict`` into PostgreSQL, Neo4j,
and OpenSearch, verify each round-trip, and confirm the Neo4j upserts are
idempotent.

Runs only when the full docker-compose stack is up. Marked with
``@pytest.mark.integration`` so ``uv run pytest`` (unit-only) skips it by
default; CI flips it on by setting ``ENV=ci`` which forces the module
through the pre-flight ping gate. If any ping fails the entire module is
skipped — we never want a half-up stack to produce flaky data.

All test data uses the deterministic UUID prefix
``00000000-0000-4000-8000-0000000000??`` from ``tests/fixtures/phase1/``
and is scrubbed at module teardown. The Postgres run/object/job/record
IDs are fixed so reruns are idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

pytestmark = pytest.mark.integration


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "phase1"
UPSERT_DIR = ROOT / "infra" / "neo4j" / "upserts"
REL_DIR = UPSERT_DIR / "relationships"

# Deterministic Postgres UUIDs for this test (distinct from fixture UUIDs).
PG_RUN_ID = UUID("00000000-0000-4000-8000-0000000000a1")
PG_OBJECT_ID = UUID("00000000-0000-4000-8000-0000000000a2")
PG_JOB_ID = UUID("00000000-0000-4000-8000-0000000000a3")
PG_RECORD_ID = UUID("00000000-0000-4000-8000-0000000000a4")


def _ping_stack() -> list[str]:
    """Return the list of services that are NOT reachable.

    Empty list ⇒ stack is healthy enough to run this test.
    """

    failures: list[str] = []
    try:
        from civic_clients import postgres as pg_client
        from civic_clients import neo4j as neo_client
        from civic_clients import opensearch as os_client
        from civic_clients import minio_client as mn_client
    except Exception as exc:  # pragma: no cover - import-time only
        return [f"civic_clients import: {exc!r}"]

    for name, ping in (
        ("postgres", pg_client.ping),
        ("neo4j", neo_client.ping),
        ("opensearch", os_client.ping),
        ("minio", mn_client.ping),
    ):
        try:
            if not ping():
                failures.append(name)
        except Exception as exc:
            failures.append(f"{name}: {exc!r}")
    return failures


_failed = _ping_stack()
if _failed:
    pytest.skip(
        f"Phase-1 integration stack not ready: {_failed}; "
        "start it with `make up` and retry.",
        allow_module_level=True,
    )


# ---- fixtures -------------------------------------------------------------


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixtures() -> dict[str, dict[str, Any]]:
    return {
        "person": _load("person"),
        "office": _load("office"),
        "membership_term": _load("membership_term"),
        "source_document": _load("source_document"),
        "evidence_span": _load("evidence_span"),
        "atomic_claim": _load("atomic_claim"),
        "verdict": _load("verdict"),
    }


@pytest.fixture(scope="module")
def pg_conn():
    from civic_clients import postgres as pg_client

    conn = pg_client.make_connection()
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="module")
def neo4j_driver():
    from civic_clients import neo4j as neo_client

    driver = neo_client.make_driver()
    yield driver
    # Driver is process-cached; do not close here.


@pytest.fixture(scope="module")
def os_client():
    from civic_clients import opensearch as os_mod

    return os_mod.make_client()


@pytest.fixture(scope="module")
def minio_client():
    from civic_clients import minio_client as mn_mod

    return mn_mod.make_client()


# ---- 1. fixture validation ------------------------------------------------


def test_fixtures_validate_via_pydantic(fixtures: dict[str, dict[str, Any]]) -> None:
    from civic_ontology import (
        AtomicClaim,
        EvidenceSpan,
        MembershipTerm,
        Office,
        Person,
        SourceDocument,
        Verdict,
    )

    Person.model_validate(fixtures["person"])
    Office.model_validate(fixtures["office"])
    MembershipTerm.model_validate(fixtures["membership_term"])
    SourceDocument.model_validate(fixtures["source_document"])
    EvidenceSpan.model_validate(fixtures["evidence_span"])
    AtomicClaim.model_validate(fixtures["atomic_claim"])
    Verdict.model_validate(fixtures["verdict"])


# ---- 2. Postgres round-trip ----------------------------------------------


def test_postgres_round_trip(pg_conn, fixtures: dict[str, dict[str, Any]]) -> None:
    src = fixtures["source_document"]
    person = fixtures["person"]

    with pg_conn.cursor() as cur:
        # ingest_runs
        cur.execute(
            """
            INSERT INTO ingest_runs (run_id, source_family, status, stats)
            VALUES (%s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (
                str(PG_RUN_ID),
                src["source_family"],
                "succeeded",
                json.dumps({"phase1_test": True}),
            ),
        )
        ingest_run_pk = cur.fetchone()[0]

        # raw_fetch_objects
        cur.execute(
            """
            INSERT INTO raw_fetch_objects (
              object_id, ingest_run_id, source_url, archive_uri,
              content_sha256, content_type, byte_size, source_tier
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                str(PG_OBJECT_ID),
                ingest_run_pk,
                src["url"],
                src["archive_uri"],
                src["content_sha256"],
                "text/html",
                len(src.get("body", "") or ""),
                src["source_tier"],
            ),
        )
        raw_pk = cur.fetchone()[0]

        # parse_jobs
        cur.execute(
            """
            INSERT INTO parse_jobs (
              job_id, raw_fetch_object_id, parser_name, status
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (str(PG_JOB_ID), raw_pk, "phase1-test-parser", "succeeded"),
        )
        job_pk = cur.fetchone()[0]

        # normalized_records
        cur.execute(
            """
            INSERT INTO normalized_records (
              record_id, parse_job_id, record_kind, payload, source_tier
            ) VALUES (%s, %s, %s, %s::jsonb, %s)
            RETURNING id
            """,
            (
                str(PG_RECORD_ID),
                job_pk,
                "person",
                json.dumps(person),
                person["source_tier"],
            ),
        )
        rec_pk = cur.fetchone()[0]

    pg_conn.commit()

    with pg_conn.cursor() as cur:
        cur.execute("SELECT run_id FROM ingest_runs WHERE id = %s", (ingest_run_pk,))
        assert str(cur.fetchone()[0]) == str(PG_RUN_ID)

        cur.execute(
            "SELECT content_sha256, archive_uri FROM raw_fetch_objects WHERE id = %s",
            (raw_pk,),
        )
        got_sha, got_uri = cur.fetchone()
        assert got_sha == src["content_sha256"]
        assert got_uri == src["archive_uri"]

        cur.execute("SELECT status FROM parse_jobs WHERE id = %s", (job_pk,))
        assert cur.fetchone()[0] == "succeeded"

        cur.execute(
            "SELECT record_kind, payload->>'person_id' FROM normalized_records WHERE id = %s",
            (rec_pk,),
        )
        kind, pid = cur.fetchone()
        assert kind == "person"
        assert pid == person["person_id"]


# ---- 3. Neo4j round-trip --------------------------------------------------


def _run_template(driver, path: Path, params: dict[str, Any]) -> list[dict[str, Any]]:
    cypher = path.read_text(encoding="utf-8")
    with driver.session() as sess:
        return [r.data() for r in sess.run(cypher, **params)]


def _person_params(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "person_id": p["person_id"],
        "canonical_name": p.get("canonical_name"),
        "hebrew_name": p.get("hebrew_name"),
        "english_name": p.get("english_name"),
        "external_ids": p.get("external_ids"),
        "source_tier": p.get("source_tier"),
    }


def _office_params(o: dict[str, Any]) -> dict[str, Any]:
    return {
        "office_id": o["office_id"],
        "canonical_name": o.get("canonical_name"),
        "office_type": o.get("office_type"),
        "scope": o.get("scope"),
    }


def _membership_term_params(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "membership_term_id": m["membership_term_id"],
        "person_id": m.get("person_id"),
        "org_id": m.get("org_id"),
        "org_type": m.get("org_type"),
        "valid_from": m.get("valid_from"),
        "valid_to": m.get("valid_to"),
    }


def _source_document_params(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": s["document_id"],
        "source_family": s.get("source_family"),
        "source_tier": s.get("source_tier"),
        "source_type": s.get("source_type"),
        "url": s.get("url"),
        "archive_uri": s.get("archive_uri"),
        "content_sha256": s.get("content_sha256"),
        "captured_at": s.get("captured_at"),
        "language": s.get("language"),
        "title": s.get("title"),
    }


def _evidence_span_params(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "span_id": e["span_id"],
        "document_id": e.get("document_id"),
        "source_tier": e.get("source_tier"),
        "source_type": e.get("source_type"),
        "url": e.get("url"),
        "archive_uri": e.get("archive_uri"),
        "text": e.get("text"),
        "char_start": e.get("char_start"),
        "char_end": e.get("char_end"),
        "captured_at": e.get("captured_at"),
    }


def _atomic_claim_params(c: dict[str, Any]) -> dict[str, Any]:
    ts = c.get("time_scope") or {}
    return {
        "claim_id": c["claim_id"],
        "raw_text": c.get("raw_text"),
        "normalized_text": c.get("normalized_text"),
        "claim_type": c.get("claim_type"),
        "speaker_person_id": c.get("speaker_person_id"),
        "target_person_id": c.get("target_person_id"),
        "bill_id": c.get("bill_id"),
        "committee_id": c.get("committee_id"),
        "office_id": c.get("office_id"),
        "vote_value": c.get("vote_value"),
        "time_scope_start": ts.get("start"),
        "time_scope_end": ts.get("end"),
        "time_scope_granularity": ts.get("granularity"),
        "checkability": c.get("checkability"),
        "created_at": c.get("created_at"),
    }


def _verdict_params(v: dict[str, Any]) -> dict[str, Any]:
    conf = v.get("confidence") or {}
    return {
        "verdict_id": v["verdict_id"],
        "claim_id": v.get("claim_id"),
        "status": v.get("status"),
        "confidence_overall": conf.get("overall"),
        "confidence_source_authority": conf.get("source_authority"),
        "confidence_directness": conf.get("directness"),
        "confidence_temporal_alignment": conf.get("temporal_alignment"),
        "confidence_entity_resolution": conf.get("entity_resolution"),
        "confidence_cross_source_consistency": conf.get("cross_source_consistency"),
        "summary": v.get("summary"),
        "needs_human_review": v.get("needs_human_review"),
        "model_version": v.get("model_version"),
        "ruleset_version": v.get("ruleset_version"),
        "created_at": v.get("created_at"),
    }


def test_neo4j_round_trip(neo4j_driver, fixtures: dict[str, dict[str, Any]]) -> None:
    f = fixtures

    _run_template(neo4j_driver, UPSERT_DIR / "person_upsert.cypher", _person_params(f["person"]))
    _run_template(neo4j_driver, UPSERT_DIR / "office_upsert.cypher", _office_params(f["office"]))
    _run_template(
        neo4j_driver,
        UPSERT_DIR / "membership_term_upsert.cypher",
        _membership_term_params(f["membership_term"]),
    )
    _run_template(
        neo4j_driver,
        UPSERT_DIR / "source_document_upsert.cypher",
        _source_document_params(f["source_document"]),
    )
    _run_template(
        neo4j_driver,
        UPSERT_DIR / "evidence_span_upsert.cypher",
        _evidence_span_params(f["evidence_span"]),
    )
    _run_template(
        neo4j_driver,
        UPSERT_DIR / "atomic_claim_upsert.cypher",
        _atomic_claim_params(f["atomic_claim"]),
    )
    _run_template(
        neo4j_driver,
        UPSERT_DIR / "verdict_upsert.cypher",
        _verdict_params(f["verdict"]),
    )

    # (:Person)-[:HELD_OFFICE]->(:Office)
    _run_template(
        neo4j_driver,
        REL_DIR / "held_office.cypher",
        {
            "person_id": f["person"]["person_id"],
            "office_id": f["office"]["office_id"],
            "valid_from": f["membership_term"]["valid_from"],
            "valid_to": f["membership_term"]["valid_to"],
        },
    )
    # (:SourceDocument)-[:HAS_SPAN]->(:EvidenceSpan)
    _run_template(
        neo4j_driver,
        REL_DIR / "has_span.cypher",
        {
            "document_id": f["source_document"]["document_id"],
            "span_id": f["evidence_span"]["span_id"],
        },
    )
    # (:AtomicClaim)-[:ABOUT_PERSON]->(:Person)
    _run_template(
        neo4j_driver,
        REL_DIR / "about_person.cypher",
        {
            "claim_id": f["atomic_claim"]["claim_id"],
            "person_id": f["person"]["person_id"],
        },
    )
    # (:AtomicClaim)-[:SUPPORTED_BY]->(:EvidenceSpan)
    _run_template(
        neo4j_driver,
        REL_DIR / "supported_by.cypher",
        {
            "claim_id": f["atomic_claim"]["claim_id"],
            "span_id": f["evidence_span"]["span_id"],
        },
    )
    # (:Verdict)-[:EVALUATES]->(:AtomicClaim)
    _run_template(
        neo4j_driver,
        REL_DIR / "evaluates.cypher",
        {
            "verdict_id": f["verdict"]["verdict_id"],
            "claim_id": f["atomic_claim"]["claim_id"],
        },
    )

    with neo4j_driver.session() as sess:
        # Verify each node is present.
        for label, key, value in [
            ("Person", "person_id", f["person"]["person_id"]),
            ("Office", "office_id", f["office"]["office_id"]),
            ("MembershipTerm", "membership_term_id", f["membership_term"]["membership_term_id"]),
            ("SourceDocument", "document_id", f["source_document"]["document_id"]),
            ("EvidenceSpan", "span_id", f["evidence_span"]["span_id"]),
            ("AtomicClaim", "claim_id", f["atomic_claim"]["claim_id"]),
            ("Verdict", "verdict_id", f["verdict"]["verdict_id"]),
        ]:
            rec = sess.run(
                f"MATCH (n:{label} {{{key}: $v}}) RETURN n.{key} AS k",
                v=value,
            ).single()
            assert rec is not None, f"missing node {label} {value}"
            assert rec["k"] == value

        # Verify each relationship is present.
        for cypher, params in [
            (
                "MATCH (:Person {person_id: $p})-[r:HELD_OFFICE]->(:Office {office_id: $o}) RETURN count(r) AS c",
                {"p": f["person"]["person_id"], "o": f["office"]["office_id"]},
            ),
            (
                "MATCH (:SourceDocument {document_id: $d})-[r:HAS_SPAN]->(:EvidenceSpan {span_id: $s}) RETURN count(r) AS c",
                {"d": f["source_document"]["document_id"], "s": f["evidence_span"]["span_id"]},
            ),
            (
                "MATCH (:AtomicClaim {claim_id: $c})-[r:ABOUT_PERSON]->(:Person {person_id: $p}) RETURN count(r) AS c",
                {"c": f["atomic_claim"]["claim_id"], "p": f["person"]["person_id"]},
            ),
            (
                "MATCH (:AtomicClaim {claim_id: $c})-[r:SUPPORTED_BY]->(:EvidenceSpan {span_id: $s}) RETURN count(r) AS c",
                {"c": f["atomic_claim"]["claim_id"], "s": f["evidence_span"]["span_id"]},
            ),
            (
                "MATCH (:Verdict {verdict_id: $v})-[r:EVALUATES]->(:AtomicClaim {claim_id: $c}) RETURN count(r) AS c",
                {"v": f["verdict"]["verdict_id"], "c": f["atomic_claim"]["claim_id"]},
            ),
        ]:
            rec = sess.run(cypher, **params).single()
            assert rec["c"] == 1, f"expected exactly 1 rel for query {cypher!r}"


def test_neo4j_upsert_is_idempotent(
    neo4j_driver, fixtures: dict[str, dict[str, Any]]
) -> None:
    """Re-running the Person upsert with the same params must not create a duplicate node."""

    with neo4j_driver.session() as sess:
        before = sess.run("MATCH (n:Person) RETURN count(n) AS c").single()["c"]

    _run_template(
        neo4j_driver,
        UPSERT_DIR / "person_upsert.cypher",
        _person_params(fixtures["person"]),
    )

    with neo4j_driver.session() as sess:
        after = sess.run("MATCH (n:Person) RETURN count(n) AS c").single()["c"]

    assert after == before, "person upsert must be idempotent"


# ---- 4. OpenSearch round-trip --------------------------------------------


def _index_and_get(os_client, index: str, doc_id: str, body: dict[str, Any]) -> dict[str, Any]:
    os_client.indices.create(index=index, ignore=400)
    os_client.index(index=index, id=doc_id, body=body, refresh="wait_for")
    got = os_client.get(index=index, id=doc_id)
    return got["_source"]


def test_opensearch_round_trip(os_client, fixtures: dict[str, dict[str, Any]]) -> None:
    src = fixtures["source_document"]
    span = fixtures["evidence_span"]
    claim = fixtures["atomic_claim"]

    src_body = {k: v for k, v in src.items()}
    span_body = {k: v for k, v in span.items()}

    # claim_cache template expects flat time_scope.{start,end,granularity}.
    claim_body = {k: v for k, v in claim.items() if k != "time_scope"}
    if claim.get("time_scope"):
        claim_body["time_scope"] = claim["time_scope"]

    got_src = _index_and_get(os_client, "source_documents", src["document_id"], src_body)
    assert got_src["document_id"] == src["document_id"]
    assert got_src["content_sha256"] == src["content_sha256"]

    got_span = _index_and_get(os_client, "evidence_spans", span["span_id"], span_body)
    assert got_span["span_id"] == span["span_id"]
    assert got_span["archive_uri"] == span["archive_uri"]

    got_claim = _index_and_get(os_client, "claim_cache", claim["claim_id"], claim_body)
    assert got_claim["claim_id"] == claim["claim_id"]
    assert got_claim["claim_type"] == claim["claim_type"]


# ---- 5. teardown ----------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _cleanup(request, fixtures: dict[str, dict[str, Any]]):
    """Scrub every Postgres row / Neo4j node / OpenSearch index we touched."""

    yield

    ids = [fixtures[k][key] for k, key in [
        ("person", "person_id"),
        ("office", "office_id"),
        ("membership_term", "membership_term_id"),
        ("source_document", "document_id"),
        ("evidence_span", "span_id"),
        ("atomic_claim", "claim_id"),
        ("verdict", "verdict_id"),
    ]]

    # Neo4j
    try:
        from civic_clients import neo4j as neo_client

        with neo_client.make_driver().session() as sess:
            sess.run(
                """
                MATCH (n)
                WHERE n.person_id IN $ids
                   OR n.office_id IN $ids
                   OR n.membership_term_id IN $ids
                   OR n.document_id IN $ids
                   OR n.span_id IN $ids
                   OR n.claim_id IN $ids
                   OR n.verdict_id IN $ids
                DETACH DELETE n
                """,
                ids=ids,
            )
    except Exception:
        pass

    # Postgres (reverse FK order)
    try:
        from civic_clients import postgres as pg_client

        with pg_client.make_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM normalized_records WHERE record_id = %s",
                (str(PG_RECORD_ID),),
            )
            cur.execute(
                "DELETE FROM parse_jobs WHERE job_id = %s", (str(PG_JOB_ID),)
            )
            cur.execute(
                "DELETE FROM raw_fetch_objects WHERE object_id = %s",
                (str(PG_OBJECT_ID),),
            )
            cur.execute(
                "DELETE FROM ingest_runs WHERE run_id = %s", (str(PG_RUN_ID),)
            )
            conn.commit()
    except Exception:
        pass

    # OpenSearch — drop the indices entirely so later runs start clean.
    try:
        from civic_clients import opensearch as os_mod

        os_mod.make_client().indices.delete(
            index=["source_documents", "evidence_spans", "claim_cache"],
            ignore=[400, 404],
        )
    except Exception:
        pass
