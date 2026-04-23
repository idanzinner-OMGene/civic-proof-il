"""Parser for Knesset ``KNS_Bill`` OData rows.

The real Bill table is flat bill-metadata only; initiators are
published as a separate entity (``KNS_BillInitiator``) and joined by
Phase-3. We therefore parse bill metadata only, and downstream
normalization emits a Bill node with an empty sponsorships tuple.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_bills"]


def parse_bills(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        if not row.get("BillID"):
            continue
        yield {
            "bill_id_external": str(row["BillID"]),
            "title_he": row.get("Name"),
            "knesset_number": row.get("KnessetNum"),
            "sub_type": row.get("SubTypeDesc"),
            "status_id": row.get("StatusID"),
            "publication_date": row.get("PublicationDate"),
        }
