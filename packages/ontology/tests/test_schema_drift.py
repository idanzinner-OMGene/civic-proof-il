"""Prove zero drift between Pydantic models and hand-written JSON Schemas.

Uses :func:`civic_ontology.schemas.check_schemas`, which:

- parses every ``*.schema.json`` and validates it against the Draft 2020-12
  metaschema;
- for each Pydantic model, asserts the paired schema's ``properties`` ⊇ model
  fields and its ``required`` list matches the model's required fields.
"""

from __future__ import annotations

from pathlib import Path

from civic_ontology.schemas import MODEL_TO_SCHEMA, check_schemas


def test_schema_drift_zero(schema_dir: Path) -> None:
    exit_code = check_schemas(schema_dir)
    assert exit_code == 0, "schema drift detected — see captured stdout"


def test_every_model_has_a_schema(schema_dir: Path) -> None:
    for _model, schema_name in MODEL_TO_SCHEMA.items():
        assert (schema_dir / schema_name).exists(), f"missing schema file: {schema_name}"


def test_atomic_claim_type_enum_matches_plan(schema_dir: Path) -> None:
    """Plan line 255 pins ``claim_type`` enum — must match byte-for-byte."""
    import json

    schema = json.loads((schema_dir / "atomic_claim.schema.json").read_text())
    assert schema["properties"]["claim_type"]["enum"] == [
        "vote_cast",
        "bill_sponsorship",
        "office_held",
        "committee_membership",
        "committee_attendance",
        "statement_about_formal_action",
    ]


def test_verdict_status_enum_matches_plan(schema_dir: Path) -> None:
    """Plan line 277 pins ``status`` enum — must match byte-for-byte."""
    import json

    schema = json.loads((schema_dir / "verdict.schema.json").read_text())
    assert schema["properties"]["status"]["enum"] == [
        "supported",
        "contradicted",
        "mixed",
        "insufficient_evidence",
        "non_checkable",
    ]
