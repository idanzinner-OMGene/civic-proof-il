"""Parser for ``KNS_CommitteeSession`` OData rows.

An attendance event in Phase-2 terms is "a committee session
occurred". The per-MK list of who actually attended a given session
is not exposed on the publicly-accessible OData feed (it lives either
on the bot-protected old endpoint or in the session protocol
document). Phase-3 derives attendees by parsing the protocol; here we
just materialize one ``AttendanceEvent`` per real session.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_attendance"]


def parse_attendance(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        if not row.get("CommitteeSessionID") or not row.get("CommitteeID"):
            continue
        yield {
            "session_id_external": str(row["CommitteeSessionID"]),
            "committee_id_external": str(row["CommitteeID"]),
            "knesset_number": row.get("KnessetNum"),
            "occurred_at": row.get("StartDate"),
            "finished_at": row.get("FinishDate"),
            "session_type": row.get("TypeDesc"),
            "session_url": row.get("SessionUrl"),
        }
