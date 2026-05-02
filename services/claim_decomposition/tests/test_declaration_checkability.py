"""Tests for the declaration-level checkability aggregator.

Asserts purely on the aggregation logic: how a list of per-claim
checkability strings collapses into a single ``DeclarationCheckability``
value. No domain fixtures used.
"""

from __future__ import annotations

from civic_claim_decomp import classify_declaration_checkability


def test_empty_list_yields_not_checkable() -> None:
    assert classify_declaration_checkability([]) == "not_checkable"


def test_single_checkable_yields_checkable_formal_action() -> None:
    assert classify_declaration_checkability(["checkable"]) == "checkable_formal_action"


def test_all_checkable_yields_checkable_formal_action() -> None:
    assert (
        classify_declaration_checkability(["checkable", "checkable", "checkable"])
        == "checkable_formal_action"
    )


def test_any_checkable_wins_regardless_of_others() -> None:
    # Even one checkable claim makes the declaration checkable_formal_action.
    mixed = ["checkable", "non_checkable", "insufficient_time_scope"]
    assert classify_declaration_checkability(mixed) == "checkable_formal_action"


def test_all_non_checkable_yields_not_checkable() -> None:
    assert (
        classify_declaration_checkability(["non_checkable", "non_checkable"])
        == "not_checkable"
    )


def test_all_insufficient_time_scope_yields_insufficient_time_scope() -> None:
    values = ["insufficient_time_scope", "insufficient_time_scope"]
    assert classify_declaration_checkability(values) == "insufficient_time_scope"


def test_all_insufficient_entity_resolution() -> None:
    values = ["insufficient_entity_resolution", "insufficient_entity_resolution"]
    assert classify_declaration_checkability(values) == "insufficient_entity_resolution"


def test_mixed_insufficient_failures_yields_partially_checkable() -> None:
    # A mix of time and entity failures without any checkable claim is
    # "partially_checkable" — the declaration could become checkable once
    # more information is supplied.
    mixed = ["insufficient_time_scope", "insufficient_entity_resolution"]
    assert classify_declaration_checkability(mixed) == "partially_checkable"


def test_non_checkable_plus_insufficient_time_yields_partially_checkable() -> None:
    mixed = ["non_checkable", "insufficient_time_scope"]
    assert classify_declaration_checkability(mixed) == "partially_checkable"


def test_single_insufficient_entity_resolution() -> None:
    assert (
        classify_declaration_checkability(["insufficient_entity_resolution"])
        == "insufficient_entity_resolution"
    )


def test_single_insufficient_time_scope() -> None:
    assert (
        classify_declaration_checkability(["insufficient_time_scope"])
        == "insufficient_time_scope"
    )
