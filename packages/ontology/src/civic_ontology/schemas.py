"""Schema tooling — drift check between Pydantic models and hand-written JSON Schemas.

Canonical-source approach (chosen over the regenerate-from-Pydantic option
called out in the Phase-1 plan):

* The **hand-written** JSON Schemas in ``data_contracts/jsonschemas/`` are the
  single source of truth. They hew exactly to the plan contracts
  (``AtomicClaim``, ``Verdict``, ``EvidenceSpan``) and control wire format.
* The Pydantic v2 models in :mod:`civic_ontology.models` are the Python-side
  twins. They must stay field-equivalent to the schemas.
* :func:`check_schemas` is the drift detector: it verifies every committed
  JSON Schema is valid Draft 2020-12, and that every Pydantic model's field
  set matches its paired schema's properties and required fields.

Rationale: Pydantic's ``model_json_schema`` output differs from a hand-written
Draft 2020-12 document in cosmetic but hard-to-normalize ways ($defs naming,
``title`` autoinjection, ``anyOf`` vs. ``type: ["string","null"]``, etc.).
Keeping the schemas authoritative and diffing *field sets* (not JSON bytes)
gives a cleaner zero-drift guarantee without playing whack-a-mole with the
generator.

The ``--write`` flag is intentionally a no-op that prints a reminder. The
``--check`` flag runs the drift detector and exits non-zero on any mismatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Type

from jsonschema import Draft202012Validator
from pydantic import BaseModel

from .claim_slots import SLOT_TEMPLATES
from .models import (
    AtomicClaim,
    AttendanceEvent,
    Bill,
    Committee,
    EvidenceSpan,
    MembershipTerm,
    Office,
    Party,
    Person,
    SourceDocument,
    Verdict,
    VoteEvent,
)
from .models.atomic_claim import ClaimType as _ClaimType
from typing import get_args as _get_args

MODEL_TO_SCHEMA: dict[Type[BaseModel], str] = {
    AtomicClaim: "atomic_claim.schema.json",
    AttendanceEvent: "attendance_event.schema.json",
    Bill: "bill.schema.json",
    Committee: "committee.schema.json",
    EvidenceSpan: "evidence_span.schema.json",
    MembershipTerm: "membership_term.schema.json",
    Office: "office.schema.json",
    Party: "party.schema.json",
    Person: "person.schema.json",
    SourceDocument: "source_document.schema.json",
    Verdict: "verdict.schema.json",
    VoteEvent: "vote_event.schema.json",
}


def default_schema_dir() -> Path:
    """Resolve the repo's canonical ``data_contracts/jsonschemas`` directory.

    This module lives at
    ``packages/ontology/src/civic_ontology/schemas.py`` — five parents up is
    the repo root.
    """

    return Path(__file__).resolve().parents[4] / "data_contracts" / "jsonschemas"


@dataclass
class DriftReport:
    """Collected drift findings across every (model, schema) pair."""

    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        if self.ok:
            return "OK: JSON Schemas and Pydantic models are field-equivalent."
        return "DRIFT:\n" + "\n".join(f"  - {e}" for e in self.errors)


def _model_field_sets(model_cls: Type[BaseModel]) -> tuple[set[str], set[str]]:
    """Return (all_fields, required_fields) for a Pydantic v2 model.

    A field is "required" when it has no default value and no default factory.
    """

    all_fields: set[str] = set()
    required: set[str] = set()
    for name, info in model_cls.model_fields.items():
        all_fields.add(name)
        if info.is_required():
            required.add(name)
    return all_fields, required


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_schemas(schema_dir: Path | None = None) -> int:
    """Verify all committed schemas are valid and match Pydantic models.

    Returns 0 on clean, 1 on any drift or invalid schema.
    """

    schema_dir = schema_dir or default_schema_dir()
    report = DriftReport()

    if not schema_dir.is_dir():
        report.errors.append(f"schema dir does not exist: {schema_dir}")
        print(report.render(), file=sys.stderr)
        return 1

    for schema_file in sorted(schema_dir.rglob("*.schema.json")):
        try:
            schema = _load_schema(schema_file)
        except json.JSONDecodeError as exc:
            report.errors.append(f"{schema_file.name}: invalid JSON ({exc})")
            continue
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # jsonschema raises SchemaError; catch broad to surface cleanly.
            report.errors.append(f"{schema_file.name}: not a valid Draft 2020-12 schema ({exc})")

    for model_cls, schema_name in MODEL_TO_SCHEMA.items():
        schema_path = schema_dir / schema_name
        if not schema_path.exists():
            report.errors.append(f"{schema_name}: missing file for model {model_cls.__name__}")
            continue
        schema = _load_schema(schema_path)
        schema_props = set((schema.get("properties") or {}).keys())
        schema_required = set(schema.get("required") or [])
        model_all, model_required = _model_field_sets(model_cls)

        missing_in_schema = model_all - schema_props
        extra_in_schema = schema_props - model_all
        if missing_in_schema:
            report.errors.append(
                f"{schema_name}: schema missing properties present on {model_cls.__name__}: "
                f"{sorted(missing_in_schema)}"
            )
        if extra_in_schema:
            report.errors.append(
                f"{schema_name}: schema has properties not on {model_cls.__name__}: "
                f"{sorted(extra_in_schema)}"
            )

        missing_required = model_required - schema_required
        extra_required = schema_required - model_required
        if missing_required:
            report.errors.append(
                f"{schema_name}: model {model_cls.__name__} requires fields not marked required "
                f"in schema: {sorted(missing_required)}"
            )
        if extra_required:
            report.errors.append(
                f"{schema_name}: schema requires fields not required on {model_cls.__name__}: "
                f"{sorted(extra_required)}"
            )

    for claim_type in _get_args(_ClaimType):
        if claim_type not in SLOT_TEMPLATES:
            report.errors.append(
                f"SLOT_TEMPLATES missing entry for claim_type {claim_type!r}"
            )
    extra_templates = set(SLOT_TEMPLATES.keys()) - set(_get_args(_ClaimType))
    if extra_templates:
        report.errors.append(
            f"SLOT_TEMPLATES has entries outside ClaimType enum: "
            f"{sorted(extra_templates)}"
        )

    print(report.render())
    return 0 if report.ok else 1


def generate_schemas(output_dir: Path | None = None) -> None:
    """No-op: canonical schemas are hand-written.

    Kept as a named entrypoint so downstream automation that imports
    ``civic_ontology.schemas.generate_schemas`` continues to resolve. Prints a
    reminder and returns without touching disk. If you need to regenerate,
    edit the hand-written files under ``data_contracts/jsonschemas/`` and run
    ``python -m civic_ontology.schemas --check`` to confirm parity.
    """

    target = output_dir or default_schema_dir()
    print(
        "generate_schemas: no-op. Hand-written schemas under "
        f"{target} are canonical; run --check to verify parity with Pydantic models."
    )


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="civic-ontology schema tooling (drift check / write reminder).",
    )
    parser.add_argument(
        "--schema-dir",
        type=Path,
        default=None,
        help="Override schema directory (default: repo's data_contracts/jsonschemas).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="Verify schemas parse as Draft 2020-12 and field sets match Pydantic models.",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="No-op reminder — hand-written schemas are canonical.",
    )
    args = parser.parse_args(argv)

    if args.write:
        generate_schemas(args.schema_dir)
        return 0
    return check_schemas(args.schema_dir)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
