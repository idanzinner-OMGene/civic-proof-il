"""Neo4j client — thin re-export from :mod:`civic_clients.neo4j`."""

from __future__ import annotations

from civic_clients.neo4j import make_driver, ping

get_neo4j_driver = make_driver
ping_neo4j = ping

__all__ = ["get_neo4j_driver", "make_driver", "ping", "ping_neo4j"]
