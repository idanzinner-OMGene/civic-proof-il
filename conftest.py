"""Workspace-root pytest configuration.

Loaded before every sub-conftest, this file does two things:

1. Injects credentials from the repo-level ``.env`` file so that
   ``uv run pytest`` works without manually sourcing ``.env`` first.
   Only keys that are NOT already in the environment are set, so explicit
   ``export`` overrides are always respected.

2. Remaps container-DNS hostnames to ``localhost`` for host-side test
   execution.  Tests always hit the docker-compose ports published to the
   host; if services aren't running those tests skip/fail on their own.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Load .env (passwords, bucket names, etc.)
# ---------------------------------------------------------------------------
_ENV_FILE = Path(__file__).parent / ".env"

try:
    from dotenv import dotenv_values  # python-dotenv is a dev dep

    if _ENV_FILE.exists():
        for _k, _v in dotenv_values(_ENV_FILE).items():
            if _k not in os.environ and _v is not None:
                os.environ[_k] = _v
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 2. Remap container-DNS names → localhost so tests work from the host.
#    These are ALWAYS forced to localhost regardless of what .env says,
#    because the test process runs on the host, not inside the compose network.
# ---------------------------------------------------------------------------
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["OPENSEARCH_URL"] = "http://localhost:9200"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
