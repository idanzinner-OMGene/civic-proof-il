"""OpenSearch client helpers."""

from __future__ import annotations

from functools import lru_cache

from opensearchpy import OpenSearch

from ..settings import get_settings


@lru_cache
def get_opensearch_client() -> OpenSearch:
    """Return a cached OpenSearch client."""

    settings = get_settings()
    http_auth = None
    if settings.opensearch_user:
        http_auth = (settings.opensearch_user, settings.opensearch_password or "")
    return OpenSearch(
        [settings.opensearch_url],
        http_auth=http_auth,
        verify_certs=False,
    )


def ping_opensearch() -> bool:
    """Return True if the OpenSearch cluster responds to ``ping()``."""

    try:
        return bool(get_opensearch_client().ping())
    except Exception:
        return False
