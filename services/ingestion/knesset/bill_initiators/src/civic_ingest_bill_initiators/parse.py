"""Parser for ``KNS_BillInitiator`` OData rows.

The upstream table has no ``KnessetNum`` column (filtering by it yields
HTTP 400) — the natural key is ``(BillID, PersonID, Ordinal)`` and
every row carries an ``IsInitiator`` boolean that distinguishes primary
initiators from co-signatories. v1 emits SPONSORED edges only for
``IsInitiator=True``.
"""

from __future__ import annotations

from typing import Any, Iterable

from civic_ingest import ODataPage

__all__ = ["parse_bill_initiators"]


def parse_bill_initiators(page: ODataPage) -> Iterable[dict[str, Any]]:
    for row in page.value:
        if not (
            row.get("BillInitiatorID")
            and row.get("BillID")
            and row.get("PersonID")
        ):
            continue
        if not row.get("IsInitiator"):
            continue
        yield {
            "bill_initiator_id_external": str(row["BillInitiatorID"]),
            "bill_id_external": str(row["BillID"]),
            "person_id_external": str(row["PersonID"]),
            "ordinal": row.get("Ordinal"),
        }
