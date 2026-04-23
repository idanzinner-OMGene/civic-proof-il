"""Phase-2 bill + sponsorship adapter.

Reads ``KNS_Bill`` and ``KNS_BillInitiator``; normalizes into
:class:`NormalizedBill` bundles that include the Bill node and its
``SPONSORED`` edges keyed by Person.
"""

from __future__ import annotations

from .normalize import NormalizedBill, NormalizedSponsorship, normalize_bill
from .parse import parse_bills
from .upsert import upsert_bill

__all__ = [
    "NormalizedBill",
    "NormalizedSponsorship",
    "normalize_bill",
    "parse_bills",
    "upsert_bill",
]
