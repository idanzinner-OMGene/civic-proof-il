"""Parser for the oknesset ``kns_committeesession.csv`` pipeline CSV.

Phase-2.5 switched this adapter from the Tier-1 OData
``KNS_CommitteeSession`` feed (which does not expose attendees) to the
oknesset meeting-attendees mirror, which republishes the same session
dimension enriched with an ``attended_mk_individual_ids`` JSON array
parsed from the session protocol.

Upstream schema (April 2026)::

    CommitteeSessionID, Number, KnessetNum, TypeID, TypeDesc,
    CommitteeID, Location, SessionUrl, BroadcastUrl, StartDate,
    FinishDate, Note, LastUpdatedDate, ..., committee_name, ...,
    mks, invitees, legal_advisors, manager, financial_advisors,
    attended_mk_individual_ids

Rows with an empty ``attended_mk_individual_ids`` (``[]``) still
produce an ``AttendanceEvent`` node — only the per-MK ``ATTENDED``
edges are skipped.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_attendance"]


def parse_attendance(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        session_id = (row.get("CommitteeSessionID") or "").strip() if isinstance(
            row.get("CommitteeSessionID"), str
        ) else row.get("CommitteeSessionID")
        committee_id = row.get("CommitteeID")
        if not session_id or not committee_id:
            continue
        knesset_raw = row.get("KnessetNum")
        yield {
            "session_id_external": str(session_id),
            "committee_id_external": str(committee_id),
            "knesset_number": _coerce_int(knesset_raw),
            "occurred_at": _as_iso_datetime(row.get("StartDate")),
            "finished_at": _as_iso_datetime(row.get("FinishDate")),
            "session_type": (row.get("TypeDesc") or "").strip() or None,
            "session_url": (row.get("SessionUrl") or "").strip() or None,
            "attended_mk_individual_ids_raw": row.get(
                "attended_mk_individual_ids"
            ),
        }


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_iso_datetime(value: object) -> str | None:
    if value in (None, ""):
        return None
    s = str(value).strip()
    if not s:
        return None
    if "T" in s:
        return s
    if " " in s:
        return s.replace(" ", "T", 1)
    if len(s) == 10:
        return f"{s}T00:00:00"
    return s
