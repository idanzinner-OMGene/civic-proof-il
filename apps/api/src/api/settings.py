"""Application settings — thin re-export from :mod:`civic_common.settings`.

The single source of truth now lives in ``packages/common``; this module
exists only so legacy imports such as ``from api.settings import Settings``
keep working.
"""

from __future__ import annotations

from civic_common.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
