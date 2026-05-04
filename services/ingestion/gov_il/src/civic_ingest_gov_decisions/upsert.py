"""Neo4j upsert for :class:`NormalizedGovernmentDecision`.

Each decision fires one ``run_upsert`` call against the existing
``government_decision_upsert.cypher`` template (created in PR-1).

The ``concerns.cypher`` relationship is intentionally left out of the
automated pipeline here: linking a GovernmentDecision to a specific
Person/Office requires entity resolution beyond what the BudgetKey payload
provides. The reviewer UI handles this linkage when a declaration is
verified against a decision.
"""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .types import NormalizedGovernmentDecision

__all__ = ["upsert_government_decision"]

_UPSERT_ROOT = Path(__file__).resolve().parents[5] / "infra" / "neo4j" / "upserts"

_GOV_DECISION_TEMPLATE = _UPSERT_ROOT / "government_decision_upsert.cypher"


def upsert_government_decision(decision: NormalizedGovernmentDecision) -> dict:
    """Write one government decision to Neo4j.

    Returns a summary dict with the key IDs written.
    """
    decision_id_str = str(decision.government_decision_id)

    run_upsert(
        _GOV_DECISION_TEMPLATE,
        {
            "government_decision_id": decision_id_str,
            "decision_number": decision.decision_number,
            "government_number": decision.government_number,
            "decision_date": decision.decision_date,
            "title": decision.title,
            "summary": decision.summary,
            "issuing_body": decision.issuing_body,
            "source_document_id": None,
        },
    )

    return {
        "government_decision_id": decision_id_str,
        "decision_number": decision.decision_number,
        "government_number": decision.government_number,
        "title": decision.title,
    }
