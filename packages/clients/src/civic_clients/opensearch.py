"""OpenSearch client factory + admin helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from opensearchpy import OpenSearch

from civic_common.settings import get_settings

__all__ = ["make_client", "ping", "put_index_templates"]


@lru_cache(maxsize=1)
def make_client() -> OpenSearch:
    """Return the process-wide cached OpenSearch client."""

    s = get_settings()
    http_auth: tuple[str, str] | None = None
    if s.opensearch_user:
        http_auth = (s.opensearch_user, s.opensearch_password or "")
    return OpenSearch([s.opensearch_url], http_auth=http_auth, verify_certs=False)


def ping() -> bool:
    """Return ``True`` if the OpenSearch cluster responds to ``ping``."""

    try:
        return bool(make_client().ping())
    except Exception:
        return False


def put_index_templates(root: Path) -> dict[str, Any]:
    """Upload every ``<name>.json`` file under ``root`` as an index template.

    The file basename (without ``.json``) is used as the template name; the
    file body is sent as-is. Returns a mapping ``{name: cluster_response}``.
    """

    client = make_client()
    out: dict[str, Any] = {}
    for path in sorted(Path(root).glob("*.json")):
        name = path.stem
        body = json.loads(path.read_text(encoding="utf-8"))
        out[name] = client.indices.put_index_template(name=name, body=body)
    return out
