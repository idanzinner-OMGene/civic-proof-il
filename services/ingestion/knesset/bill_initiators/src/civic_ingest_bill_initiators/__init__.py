"""Phase-2.5 bill-initiators adapter.

Joins ``KNS_BillInitiator`` (Tier-1 OData) onto the Bill and Person
nodes from earlier adapters, emitting
``(:Person)-[:SPONSORED]->(:Bill)`` edges. Co-signatory rows
(``IsInitiator=False``) are filtered out for v1 — only primary bill
initiators become ``SPONSORED`` edges.
"""

from __future__ import annotations

from .normalize import (
    PHASE2_UUID_NAMESPACE,
    NormalizedBillSponsorship,
    normalize_bill_initiator,
)
from .parse import parse_bill_initiators
from .upsert import upsert_bill_sponsorship

__all__ = [
    "NormalizedBillSponsorship",
    "PHASE2_UUID_NAMESPACE",
    "normalize_bill_initiator",
    "parse_bill_initiators",
    "upsert_bill_sponsorship",
]
