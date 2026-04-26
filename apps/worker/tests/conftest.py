"""Worker-test conftest.

Mirrors the api-tests pattern (see **Testing / pytest** in
``docs/AGENT_GUIDE.md`` — ``api.main`` / ``Settings`` at import time). Other test roots in this repo may set ``ENV=test`` at
conftest-load time; the worker's ``run_once`` unit test asserts
``env == "dev"`` on the default code path, so we pin the env here
before any worker module imports ``Settings``.
"""

from __future__ import annotations

import os

os.environ["ENV"] = "dev"
