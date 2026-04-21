"""Smoke tests asserting migrations / constraints / templates were applied."""

from __future__ import annotations

import pytest


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


def test_neo4j_constraints_applied():
    neo4j = pytest.importorskip("neo4j")
    from .conftest import NEO4J

    driver = neo4j.GraphDatabase.driver(NEO4J["uri"], auth=NEO4J["auth"])
    try:
        with driver.session() as sess:
            result = sess.run("SHOW CONSTRAINTS")
            names = {record["name"] for record in result}
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


def test_opensearch_template_registered():
    httpx = pytest.importorskip("httpx")
    from .conftest import OPENSEARCH_URL

    r = httpx.get(
        f"{OPENSEARCH_URL}/_index_template/0001_sources_template", timeout=5
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["index_templates"], body
