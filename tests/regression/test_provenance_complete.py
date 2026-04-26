"""Provenance: lexical evidence in bundles references tier metadata."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.regression

from api.routers.pipeline import VerifyPipeline


def test_pipeline_returns_consistent_shape():
    p = VerifyPipeline()
    b = p.verify("Unrelated flibble text that should not decompose to claims.", language="en")
    assert isinstance(b, list)
    for item in b:
        assert "verdict" in item
        assert "claim" in item


@pytest.mark.integration
def test_neo4j_source_documents_have_archive_uri_when_graph_reachable():
    from civic_clients import neo4j

    if not neo4j.ping():
        pytest.skip("neo4j unreachable")
    driver = neo4j.make_driver()
    with driver.session() as session:
        rec = session.run(
            "MATCH (d:SourceDocument) "
            "WHERE d.archive_uri IS NULL OR trim(toString(d.archive_uri)) = '' "
            "RETURN count(d) AS n"
        ).single()
        assert rec is not None
        assert int(rec["n"]) == 0, "every SourceDocument must carry archive_uri for provenance"
