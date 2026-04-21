"""Neo4j client helpers."""

from __future__ import annotations

from functools import lru_cache

from neo4j import GraphDatabase

from ..settings import get_settings


@lru_cache
def get_neo4j_driver():
    """Return a cached Neo4j driver instance."""

    settings = get_settings()
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def ping_neo4j() -> bool:
    """Return True if the driver can verify connectivity."""

    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False
