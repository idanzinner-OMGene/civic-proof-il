"""Set REVIEWER_UI_PASSWORD for the test process so that the auth dependency
does not return 503 during unit tests.  Tests that want to verify the 401
path should explicitly omit the auth= argument.
"""

from __future__ import annotations

import os

os.environ.setdefault("REVIEWER_UI_PASSWORD", "test_secret")
