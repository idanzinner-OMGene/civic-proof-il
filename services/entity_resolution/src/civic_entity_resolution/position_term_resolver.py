"""Date-aware resolver for PositionTerm nodes.

Answers the question: "Did person X hold office Y during time range T?"

This is a building block for declaration verification (PR-5).  It queries
the V2 ``(:Person)-[:HAS_POSITION_TERM]->(:PositionTerm)-[:ABOUT_OFFICE]->(:Office)``
path and filters by date overlap.  The legacy ``HELD_OFFICE`` edge is *not*
queried here — callers that need backward compatibility with pre-ingest
graphs should use the graph retrieval template directly.

Date parameters must be ISO-8601 strings (``YYYY-MM-DDTHH:MM:SS`` or
``YYYY-MM-DD``).  ``None`` is treated as "unbounded" on that side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "PositionTermMatch",
    "resolve_position_terms",
]


@dataclass(frozen=True, slots=True)
class PositionTermMatch:
    """One matching PositionTerm node."""

    position_term_id: str
    person_id: str
    office_id: str
    appointing_body: str | None
    valid_from: str | None
    valid_to: str | None
    is_acting: bool


def resolve_position_terms(
    neo4j_session: Any,
    *,
    person_id: str,
    office_id: str | None = None,
    as_of_date: str | None = None,
) -> list[PositionTermMatch]:
    """Return all PositionTerm nodes held by ``person_id``.

    Parameters
    ----------
    neo4j_session:
        An active Neo4j session (driver.session()).
    person_id:
        UUID string of the :class:`Person` node.
    office_id:
        Optional UUID string of the :class:`Office` node.  When supplied,
        only terms whose ``ABOUT_OFFICE`` target matches are returned.
    as_of_date:
        Optional ISO-8601 date string.  When supplied, only terms that were
        active on that date are returned — i.e. ``valid_from <= as_of_date``
        AND (``valid_to IS NULL`` OR ``valid_to >= as_of_date``).

    Returns
    -------
    list[PositionTermMatch]
        Zero or more matching position terms, ordered by ``valid_from``
        ascending (nulls last).
    """

    office_filter = ""
    if office_id is not None:
        office_filter = " AND o.office_id = $office_id"

    date_filter = ""
    if as_of_date is not None:
        date_filter = (
            " AND pt.valid_from <= datetime($as_of_date)"
            " AND (pt.valid_to IS NULL OR pt.valid_to >= datetime($as_of_date))"
        )

    cypher = (
        "MATCH (p:Person {person_id: $person_id})"
        "-[:HAS_POSITION_TERM]->(pt:PositionTerm)"
        "-[:ABOUT_OFFICE]->(o:Office)"
        f"WHERE true{office_filter}{date_filter} "
        "RETURN "
        "  pt.position_term_id AS position_term_id,"
        "  pt.person_id        AS person_id,"
        "  o.office_id         AS office_id,"
        "  pt.appointing_body  AS appointing_body,"
        "  toString(pt.valid_from) AS valid_from,"
        "  toString(pt.valid_to)   AS valid_to,"
        "  pt.is_acting        AS is_acting "
        "ORDER BY pt.valid_from ASC NULLS LAST"
    )

    params: dict[str, Any] = {"person_id": person_id}
    if office_id is not None:
        params["office_id"] = office_id
    if as_of_date is not None:
        params["as_of_date"] = as_of_date

    results: list[PositionTermMatch] = []
    for record in neo4j_session.run(cypher, **params):
        results.append(
            PositionTermMatch(
                position_term_id=str(record["position_term_id"]),
                person_id=str(record["person_id"]),
                office_id=str(record["office_id"]),
                appointing_body=record.get("appointing_body"),
                valid_from=record.get("valid_from"),
                valid_to=record.get("valid_to"),
                is_acting=bool(record.get("is_acting", False)),
            )
        )
    return results
