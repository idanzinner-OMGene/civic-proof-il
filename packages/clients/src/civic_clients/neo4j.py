"""Neo4j driver factory + upsert helper.

The driver is cached per process (Neo4j drivers are thread-safe and
internally pool connections; creating a driver per call defeats that).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import neo4j
from neo4j import GraphDatabase

from civic_common.settings import get_settings

__all__ = ["make_driver", "ping", "run_upsert"]


@lru_cache(maxsize=1)
def make_driver() -> neo4j.Driver:
    """Return the process-wide cached Neo4j driver."""

    s = get_settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))


def ping() -> bool:
    """Return ``True`` if the driver can ``verify_connectivity``."""

    try:
        make_driver().verify_connectivity()
        return True
    except Exception:
        return False


def run_upsert(template_path: Path, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute a single-statement Cypher template and return all records.

    Convention: every file under ``infra/neo4j/upserts/`` contains exactly
    one Cypher statement (owned by Agent B). This helper treats the file
    contents verbatim — no splitting on ``;`` — because the official driver
    also accepts only one statement per ``run`` call.
    """

    cypher = Path(template_path).read_text(encoding="utf-8")
    driver = make_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [record.data() for record in result]
