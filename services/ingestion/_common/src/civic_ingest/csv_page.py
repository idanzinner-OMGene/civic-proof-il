"""Helpers for CSV-format ingestion cassettes (oknesset pipelines).

Some Knesset data (votes, attendance/presence) is only published by
third-party mirrors (https://production.oknesset.org/pipelines/) as
CSV dumps. We treat a CSV dump as a single "page" — no pagination —
and expose the same :class:`~civic_ingest.odata.ODataPage` shape so
``civic_ingest.adapter.run_adapter`` works uniformly for CSV and OData
adapters alike.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from .odata import ODataPage

__all__ = ["parse_csv_page"]


def parse_csv_page(payload: bytes | str) -> ODataPage:
    """Parse a CSV dump into an :class:`ODataPage`-shaped object.

    The header row names are preserved verbatim; every row becomes a
    dict keyed by header. Never follows pagination (CSV dumps are
    single-file).
    """

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(payload))
    value: list[dict[str, Any]] = [dict(row) for row in reader]
    return ODataPage(value=value, next_link=None, total_count=len(value))
