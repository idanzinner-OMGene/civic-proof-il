"""Parser for Knesset ``KNS_Person`` OData rows.

The live ``https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Person``
feed is intentionally narrow: basic identity only. Party / faction
affiliation and office / position are modelled as separate entities
(``KNS_Faction``, ``KNS_Position``, ``KNS_PersonToPosition``) and
are joined in Phase-3. We therefore parse only the fields that are
actually present on a Person row; adding more requires a manifest +
adapter change so drift is always intentional.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_persons"]


_REQUIRED = ("PersonID",)


def parse_persons(page: ODataPage) -> Iterable[dict[str, Any]]:
    """Yield one dict per ``KNS_Person`` row.

    Silently drops rows missing ``PersonID`` (structurally broken).
    Every field that actually appears on a real row is surfaced; the
    party / office split happens in ``KNS_PersonToPosition`` (Phase-3).
    """

    for row in page.value:
        if any(row.get(k) in (None, "") for k in _REQUIRED):
            continue
        yield {
            "person_id_external": str(row["PersonID"]),
            "first_name_he": row.get("FirstName"),
            "last_name_he": row.get("LastName"),
            "gender": row.get("GenderDesc"),
            "is_current": bool(row.get("IsCurrent") or False),
            "last_updated_at": row.get("LastUpdatedDate"),
        }
