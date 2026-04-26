"""Parser for ``KNS_PersonToPosition`` OData rows.

The upstream OData table keys every row by ``PersonToPositionID`` and
contains two populated dimensions in practice: party membership (via
``FactionID``/``FactionName``) and office held (via
``PositionID``/``DutyDesc``/``GovMinistryID``). The ``CommitteeID`` /
``CommitteeName`` columns exist in the schema but are 100% NULL in the
live data, so this parser extracts but doesn't validate them — the
normalizer drops them.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_positions"]


def parse_positions(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        if not row.get("PersonToPositionID") or not row.get("PersonID"):
            continue
        yield {
            "person_to_position_id_external": str(row["PersonToPositionID"]),
            "person_id_external": str(row["PersonID"]),
            "position_id": row.get("PositionID"),
            "faction_id_external": (
                str(row["FactionID"]) if row.get("FactionID") else None
            ),
            "faction_name": row.get("FactionName"),
            "committee_id_external": (
                str(row["CommitteeID"]) if row.get("CommitteeID") else None
            ),
            "committee_name": row.get("CommitteeName"),
            "gov_ministry_id": (
                str(row["GovMinistryID"]) if row.get("GovMinistryID") else None
            ),
            "gov_ministry_name": row.get("GovMinistryName"),
            "duty_desc": row.get("DutyDesc"),
            "start_date": row.get("StartDate"),
            "finish_date": row.get("FinishDate"),
            "knesset_num": row.get("KnessetNum"),
            "is_current": row.get("IsCurrent"),
        }
