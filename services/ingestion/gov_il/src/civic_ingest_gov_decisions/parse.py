"""Parser for the BudgetKey government decisions API response.

Parses a JSON response from::

    GET https://next.obudget.org/search/gov_decisions?q=...&size=N&from=M

The response shape is::

    {
        "search_counts": {"_current": {"total_overall": N}, ...},
        "search_results": [
            {"score": 1.0, "source": {...}, "type": "gov_decisions"},
            ...
        ]
    }

Each ``source`` object is normalised into a :class:`BudgetKeyDecisionRow`.

Only records whose ``policy_type`` contains "החלטות" are kept — this
filters out procedural guidelines (נהלים), instructions (הנחיות), and
inter-committee decisions that are not formal cabinet decisions.
"""

from __future__ import annotations

import json
from typing import Iterable

from .types import BudgetKeyDecisionRow

__all__ = ["parse_response", "total_overall"]

def _is_formal_decision(source: dict) -> bool:
    """Return True if ``source`` represents a formal cabinet-level decision."""
    policy_type = source.get("policy_type") or ""
    return any(t in policy_type for t in ("החלטות",))


def parse_response(json_bytes: bytes) -> list[BudgetKeyDecisionRow]:
    """Parse a BudgetKey API JSON response into :class:`BudgetKeyDecisionRow` objects.

    Filters to formal cabinet decisions only.

    Parameters
    ----------
    json_bytes:
        Raw bytes of the BudgetKey JSON response.

    Returns
    -------
    list[BudgetKeyDecisionRow]
        One entry per formal decision in the response page.
    """
    data = json.loads(json_bytes)
    results = data.get("search_results", [])
    rows: list[BudgetKeyDecisionRow] = []
    for hit in results:
        source = hit.get("source") or {}
        if not _is_formal_decision(source):
            continue
        row = _source_to_row(source)
        if row is not None:
            rows.append(row)
    return rows


def total_overall(json_bytes: bytes) -> int:
    """Return the total number of matching records reported by the API."""
    data = json.loads(json_bytes)
    return int(
        data.get("search_counts", {})
        .get("_current", {})
        .get("total_overall", 0)
    )


def parse_all_rows(json_bytes: bytes) -> Iterable[BudgetKeyDecisionRow]:
    """Yield all rows (alias for :func:`parse_response` to match elections style)."""
    yield from parse_response(json_bytes)


def _source_to_row(source: dict) -> BudgetKeyDecisionRow | None:
    budgetkey_id = source.get("id")
    if not budgetkey_id:
        return None
    title = (source.get("title") or "").strip()
    if not title:
        return None

    return BudgetKeyDecisionRow(
        budgetkey_id=str(budgetkey_id),
        procedure_number_str=source.get("procedure_number_str") or None,
        government_raw=source.get("government") or None,
        publish_date=source.get("publish_date") or None,
        title=title,
        text=source.get("text") or None,
        office=source.get("office") or None,
        policy_type=source.get("policy_type") or None,
        url_id=source.get("url_id") or None,
    )
