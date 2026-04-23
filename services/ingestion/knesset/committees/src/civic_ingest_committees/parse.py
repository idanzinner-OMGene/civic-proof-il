"""Parser for Knesset ``KNS_Committee`` OData rows.

The real ``KNS_Committee`` feed is a flat committee-metadata table —
it does not embed members. Committee membership is modelled via
``KNS_PersonToPosition`` and resolved in Phase-3. We therefore parse
committee metadata only; downstream normalization emits a committee
node without a members list (which matches the real data shape).
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_committees"]


def parse_committees(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        if not row.get("CommitteeID"):
            continue
        yield {
            "committee_id_external": str(row["CommitteeID"]),
            "name_he": row.get("Name"),
            "knesset_number": row.get("KnessetNum"),
            "committee_type": row.get("CommitteeTypeDesc"),
            "start_date": row.get("StartDate"),
            "end_date": row.get("FinishDate"),
            "is_current": bool(row.get("IsCurrent") or False),
        }
