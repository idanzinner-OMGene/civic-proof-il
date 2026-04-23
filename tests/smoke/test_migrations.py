"""Smoke tests asserting migrations / constraints / templates were applied.

Phase 0 baseline: ``schema_migrations_info`` table, the eight legacy Neo4j
``*_id_unique`` constraints, and the old placeholder OpenSearch template.

Phase 1 extensions (plan lines 204-246):
- All nine Postgres domain tables from ``0002_phase1_domain_schema``.
- All 12 Neo4j node ``*_id_unique`` constraints (property-existence constraints
  are Enterprise-only in Neo4j 5, so only uniqueness is enforced declaratively;
  required-property enforcement lives in the MERGE templates).
- All three OpenSearch index templates (``0001_source_documents``,
  ``0002_evidence_spans``, ``0003_claim_cache``).
"""

from __future__ import annotations

import pytest

PHASE1_PG_TABLES = {
    "ingest_runs",
    "raw_fetch_objects",
    "parse_jobs",
    "normalized_records",
    "entity_candidates",
    "review_tasks",
    "review_actions",
    "verification_runs",
    "verdict_exports",
}

PHASE1_NEO4J_UNIQUE = {
    "person_id_unique",
    "party_id_unique",
    "office_id_unique",
    "committee_id_unique",
    "bill_id_unique",
    "vote_event_id_unique",
    "attendance_event_id_unique",
    "membership_term_id_unique",
    "source_document_id_unique",
    "evidence_span_id_unique",
    "atomic_claim_id_unique",
    "verdict_id_unique",
}

PHASE1_OPENSEARCH_TEMPLATES = {
    "0001_source_documents",
    "0002_evidence_spans",
    "0003_claim_cache",
}

PHASE2_PG_TABLES = {"jobs", "entity_aliases"}


def test_postgres_migration_applied():
    psycopg = pytest.importorskip("psycopg")
    from .conftest import POSTGRES

    with psycopg.connect(**POSTGRES, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'schema_migrations_info'"
            )
            assert cur.fetchone() is not None


def test_postgres_phase1_tables_exist():
    psycopg = pytest.importorskip("psycopg")
    from .conftest import POSTGRES

    with psycopg.connect(**POSTGRES, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        tables = {row[0] for row in cur.fetchall()}
    missing = PHASE1_PG_TABLES - tables
    assert not missing, f"missing Phase-1 tables: {missing}"


def test_postgres_phase2_tables_exist():
    psycopg = pytest.importorskip("psycopg")
    from .conftest import POSTGRES

    with psycopg.connect(**POSTGRES, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        tables = {row[0] for row in cur.fetchall()}
    missing = PHASE2_PG_TABLES - tables
    assert not missing, f"missing Phase-2 tables: {missing}"


def test_neo4j_constraints_applied():
    neo4j = pytest.importorskip("neo4j")
    from .conftest import NEO4J

    driver = neo4j.GraphDatabase.driver(NEO4J["uri"], auth=NEO4J["auth"])
    try:
        with driver.session() as sess:
            result = sess.run("SHOW CONSTRAINTS")
            names = {record["name"] for record in result}
            # Phase-0 baseline set (eight legacy unique constraints).
            expected = {
                "person_id_unique",
                "party_id_unique",
                "office_id_unique",
                "committee_id_unique",
                "bill_id_unique",
                "source_document_id_unique",
                "atomic_claim_id_unique",
                "verdict_id_unique",
            }
            missing = expected - names
            assert not missing, f"missing constraints: {missing}"
    finally:
        driver.close()


def test_neo4j_phase1_unique_constraints():
    neo4j = pytest.importorskip("neo4j")
    from .conftest import NEO4J

    driver = neo4j.GraphDatabase.driver(NEO4J["uri"], auth=NEO4J["auth"])
    try:
        with driver.session() as sess:
            names = {r["name"] for r in sess.run("SHOW CONSTRAINTS")}
        missing = PHASE1_NEO4J_UNIQUE - names
        assert not missing, f"missing Phase-1 unique constraints: {missing}"
    finally:
        driver.close()


@pytest.mark.parametrize("template_name", sorted(PHASE1_OPENSEARCH_TEMPLATES))
def test_opensearch_phase1_templates_registered(template_name: str):
    httpx = pytest.importorskip("httpx")
    from .conftest import OPENSEARCH_URL

    r = httpx.get(f"{OPENSEARCH_URL}/_index_template/{template_name}", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["index_templates"], body
