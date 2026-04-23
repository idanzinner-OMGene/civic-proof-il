"""Infrastructure clients — thin wrappers over :mod:`civic_clients`.

Re-exported here so legacy imports (``from api.clients.postgres import …``)
and the health-endpoint monkeypatches keep working unchanged.
"""

from . import minio_client, neo4j_client, opensearch_client, postgres

__all__ = ["minio_client", "neo4j_client", "opensearch_client", "postgres"]
