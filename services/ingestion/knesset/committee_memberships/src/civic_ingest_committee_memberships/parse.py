"""Parser for ``mk_individual_committees.csv`` (oknesset pipelines CSV).

The CSV schema (as of April 2026) is::

    mk_individual_id,committee_id,committee_name,position_id,
    position_name,start_date,finish_date,knesset

All eight columns are preserved verbatim; the normalizer consumes them.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_committee_memberships"]


def parse_committee_memberships(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        mk_id = (row.get("mk_individual_id") or "").strip()
        committee_id = (row.get("committee_id") or "").strip()
        if not mk_id or not committee_id:
            continue
        yield {
            "mk_individual_id": mk_id,
            "committee_id_external": committee_id,
            "committee_name": (row.get("committee_name") or "").strip() or None,
            "position_id": row.get("position_id") or None,
            "position_name": (row.get("position_name") or "").strip() or None,
            "start_date": (row.get("start_date") or "").strip() or None,
            "finish_date": (row.get("finish_date") or "").strip() or None,
            "knesset": row.get("knesset") or None,
        }
