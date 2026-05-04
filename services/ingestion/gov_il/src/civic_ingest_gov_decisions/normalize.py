"""Normalize parsed BudgetKey rows → :class:`NormalizedGovernmentDecision`.

Responsibilities:

- Compute deterministic ``government_decision_id`` via
  ``uuid5(NS, "budgetkey_gov_decision:{budgetkey_id}")``.
- Parse ``government_number`` from the Hebrew text "הממשלה ה- 37".
- Truncate ``text`` to first 2000 characters for the ``summary`` field.
- Build provenance URL from ``url_id``.
"""

from __future__ import annotations

import re
import uuid
from typing import Iterable

from .types import PHASE2_UUID_NAMESPACE, BudgetKeyDecisionRow, NormalizedGovernmentDecision

__all__ = ["normalize_decision", "normalize_rows"]

_GOV_NUMBER_RE = re.compile(r"ה-?\s*(\d+)")
_GOVIL_BASE_URL = "https://www.gov.il/he/departments/policies/"
_SUMMARY_MAX_CHARS = 2000


def normalize_decision(row: BudgetKeyDecisionRow) -> NormalizedGovernmentDecision:
    """Normalize one :class:`BudgetKeyDecisionRow` into a canonical record.

    The UUID key is deterministic: re-running normalization on the same
    upstream record always produces the same ``government_decision_id``.
    """
    government_decision_id = uuid.uuid5(
        PHASE2_UUID_NAMESPACE,
        f"budgetkey_gov_decision:{row.budgetkey_id}",
    )

    government_number = _parse_government_number(row.government_raw)

    summary: str | None = None
    if row.text:
        text = row.text.strip()
        summary = text[:_SUMMARY_MAX_CHARS] if len(text) > _SUMMARY_MAX_CHARS else text

    source_url: str | None = None
    if row.url_id:
        source_url = _GOVIL_BASE_URL + row.url_id

    return NormalizedGovernmentDecision(
        government_decision_id=government_decision_id,
        decision_number=row.procedure_number_str,
        government_number=government_number,
        decision_date=row.publish_date,
        title=row.title,
        summary=summary,
        issuing_body=row.office,
        source_url=source_url,
    )


def normalize_rows(rows: Iterable[BudgetKeyDecisionRow]) -> Iterable[NormalizedGovernmentDecision]:
    """Yield one :class:`NormalizedGovernmentDecision` per row."""
    for row in rows:
        yield normalize_decision(row)


def _parse_government_number(government_raw: str | None) -> int | None:
    """Extract integer government number from Hebrew text like 'הממשלה ה- 37'."""
    if not government_raw:
        return None
    m = _GOV_NUMBER_RE.search(government_raw)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None
