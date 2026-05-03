"""Tests for civic_verification.relation_rules — verdict-to-relation mapping and confidence bands."""

from __future__ import annotations

from civic_verification.relation_rules import (
    determine_confidence_band,
    determine_relation,
    worst_relation,
)


# --- determine_relation: base mapping ---


def test_supported_maps_to_supported_by() -> None:
    assert (
        determine_relation(
            verdict_status="supported",
            checkability="checkable",
            reasons=[],
            lexical_hits=0,
        )
        == "supported_by"
    )


def test_contradicted_maps_to_contradicted_by() -> None:
    assert (
        determine_relation(
            verdict_status="contradicted",
            checkability="checkable",
            reasons=[],
            lexical_hits=0,
        )
        == "contradicted_by"
    )


def test_mixed_maps_to_overstates() -> None:
    assert (
        determine_relation(
            verdict_status="mixed",
            checkability="checkable",
            reasons=[],
            lexical_hits=2,
        )
        == "overstates"
    )


def test_insufficient_evidence_maps_to_not_checkable() -> None:
    assert (
        determine_relation(
            verdict_status="insufficient_evidence",
            checkability="checkable",
            reasons=[],
            lexical_hits=0,
        )
        == "not_checkable_against_record"
    )


def test_non_checkable_maps_to_not_checkable() -> None:
    assert (
        determine_relation(
            verdict_status="non_checkable",
            checkability="non_checkable",
            reasons=[],
            lexical_hits=0,
        )
        == "not_checkable_against_record"
    )


# --- determine_relation: refinement rules ---


def test_refinement_entity_ambiguous() -> None:
    assert (
        determine_relation(
            verdict_status="non_checkable",
            checkability="insufficient_entity_resolution",
            reasons=[],
            lexical_hits=0,
        )
        == "entity_ambiguous"
    )


def test_refinement_time_scope_from_checkability() -> None:
    assert (
        determine_relation(
            verdict_status="non_checkable",
            checkability="insufficient_time_scope",
            reasons=[],
            lexical_hits=0,
        )
        == "time_scope_mismatch"
    )


def test_refinement_time_scope_from_reason() -> None:
    assert (
        determine_relation(
            verdict_status="contradicted",
            checkability="checkable",
            reasons=[{"reason": "time_scope_issue"}],
            lexical_hits=0,
        )
        == "time_scope_mismatch"
    )


def test_refinement_underspecifies() -> None:
    assert (
        determine_relation(
            verdict_status="mixed",
            checkability="checkable",
            reasons=[],
            lexical_hits=1,
        )
        == "underspecifies"
    )


def test_unknown_verdict_defaults() -> None:
    assert (
        determine_relation(
            verdict_status="some_unknown_value",
            checkability="checkable",
            reasons=[],
            lexical_hits=0,
        )
        == "not_checkable_against_record"
    )


# --- determine_confidence_band ---


def test_confidence_band_high() -> None:
    assert determine_confidence_band(0.85) == "high"


def test_confidence_band_medium() -> None:
    assert determine_confidence_band(0.65) == "medium"


def test_confidence_band_low() -> None:
    assert determine_confidence_band(0.50) == "low"


def test_confidence_band_uncertain() -> None:
    assert determine_confidence_band(0.30) == "uncertain"


def test_confidence_band_boundary_high() -> None:
    assert determine_confidence_band(0.8) == "high"


def test_confidence_band_boundary_medium() -> None:
    assert determine_confidence_band(0.6) == "medium"


def test_confidence_band_boundary_low() -> None:
    assert determine_confidence_band(0.45) == "low"


# --- worst_relation ---


def test_worst_relation_picks_lowest_priority() -> None:
    assert worst_relation(["supported_by", "contradicted_by"]) == "contradicted_by"


def test_worst_relation_empty_returns_default() -> None:
    assert worst_relation([]) == "not_checkable_against_record"


def test_worst_relation_single() -> None:
    assert worst_relation(["overstates"]) == "overstates"
