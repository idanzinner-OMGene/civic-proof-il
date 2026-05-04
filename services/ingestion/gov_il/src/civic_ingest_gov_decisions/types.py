"""Interface dataclasses shared across parse / normalize / upsert layers.

Defining them here breaks the dependency cycle so all three modules can be
developed and tested independently against the same contract.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

__all__ = [
    "PHASE2_UUID_NAMESPACE",
    "BudgetKeyDecisionRow",
    "NormalizedGovernmentDecision",
]

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


@dataclass(frozen=True, slots=True)
class BudgetKeyDecisionRow:
    """One raw decision record from the BudgetKey API response."""

    # BudgetKey-internal UUID for this record
    budgetkey_id: str
    # Official decision number, e.g. "2084", "712", "210/2023" (nullable)
    procedure_number_str: str | None
    # Issuing government, e.g. "הממשלה ה- 37" (nullable raw string)
    government_raw: str | None
    # ISO-8601 publication date
    publish_date: str | None
    # Hebrew title
    title: str
    # Full decision body (nullable, may be long)
    text: str | None
    # Issuing office, e.g. "משרד ראש הממשלה"
    office: str | None
    # Classification, e.g. "החלטות ממשלה", "נהלים והנחיות"
    policy_type: str | None
    # gov.il page slug for provenance
    url_id: str | None


@dataclass(frozen=True, slots=True)
class NormalizedGovernmentDecision:
    """Normalized record ready for Neo4j upsert — one per decision."""

    government_decision_id: uuid.UUID
    decision_number: str | None
    government_number: int | None
    decision_date: str | None
    title: str
    summary: str | None
    issuing_body: str | None
    # Provenance: gov.il canonical URL derived from url_id
    source_url: str | None
