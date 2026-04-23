"""Parser for per-MK vote rows.

Source: ``vote_rslts_kmmbr_shadow.csv`` at
``https://production.oknesset.org/pipelines/data/votes/``. One row
per ``(vote_id, kmmbr_id, vote_result)`` — the Knesset's authoritative
OData feed for individual member votes is behind a bot challenge, so
this open-government CSV dump is the realistic data source.

Each CSV row becomes one "detail" line on a ``VoteEvent`` grouped by
``vote_id`` — grouping happens in ``normalize_vote`` so one parse pass
can feed the normalizer row-by-row without buffering the whole CSV
in adapter memory.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_votes"]


def parse_votes(page: ODataPage) -> Iterable[dict[str, Any]]:
    """Yield one dict per CSV row.

    Drops rows that are missing ``vote_id`` or ``kmmbr_id``
    (structurally broken — can't be anchored to a VoteEvent node).
    """

    for row in page.value:
        vote_id = row.get("vote_id")
        kmmbr_id = row.get("kmmbr_id")
        if not vote_id or not kmmbr_id:
            continue
        try:
            vote_result = int(row.get("vote_result") or 0)
        except (TypeError, ValueError):
            vote_result = 0
        try:
            knesset_num = int(row["knesset_num"]) if row.get("knesset_num") else None
        except (TypeError, ValueError):
            knesset_num = None
        yield {
            "vote_id_external": str(vote_id),
            "person_id_external": str(kmmbr_id).lstrip("0") or "0",
            "person_name_he": row.get("kmmbr_name"),
            "vote_result": vote_result,
            "knesset_number": knesset_num,
            "faction_id_external": (
                str(row["faction_id"]) if row.get("faction_id") else None
            ),
            "faction_name_he": row.get("faction_name"),
        }
