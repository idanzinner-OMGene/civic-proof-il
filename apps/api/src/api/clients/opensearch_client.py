"""OpenSearch client — thin re-export from :mod:`civic_clients.opensearch`."""

from __future__ import annotations

from civic_clients.opensearch import make_client, ping

get_opensearch_client = make_client
ping_opensearch = ping

__all__ = ["get_opensearch_client", "make_client", "ping", "ping_opensearch"]
