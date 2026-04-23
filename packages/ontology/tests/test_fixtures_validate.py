"""Validate every phase-1 JSON fixture against its canonical JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

FIXTURE_TO_SCHEMA: dict[str, str] = {
    "person.json": "person.schema.json",
    "office.json": "office.schema.json",
    "party.json": "party.schema.json",
    "committee.json": "committee.schema.json",
    "bill.json": "bill.schema.json",
    "vote_event.json": "vote_event.schema.json",
    "attendance_event.json": "attendance_event.schema.json",
    "membership_term.json": "membership_term.schema.json",
    "source_document.json": "source_document.schema.json",
    "evidence_span.json": "evidence_span.schema.json",
    "atomic_claim.json": "atomic_claim.schema.json",
    "verdict.json": "verdict.schema.json",
}


def _build_registry(schema_dir: Path) -> Registry:
    """Register every schema file under ``schema_dir`` so ``$ref`` resolves.

    We register each schema twice: once under its declared ``$id`` (an
    absolute URL) and once under the relative path from ``schema_dir``
    (e.g. ``common/source_tier.schema.json``). The relative path form is
    what the contracts emit when they ``$ref`` other files in the same
    directory tree.
    """

    resources: list[tuple[str, Resource]] = []
    for schema_file in schema_dir.rglob("*.schema.json"):
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        resource = Resource(contents=schema, specification=DRAFT202012)
        rel = schema_file.relative_to(schema_dir).as_posix()
        resources.append((rel, resource))
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, resource))
    return Registry().with_resources(resources)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture_name,schema_name", sorted(FIXTURE_TO_SCHEMA.items()))
def test_fixture_validates(
    fixture_name: str,
    schema_name: str,
    fixtures_dir: Path,
    schema_dir: Path,
) -> None:
    fixture_path = fixtures_dir / fixture_name
    schema_path = schema_dir / schema_name
    assert fixture_path.exists(), f"missing fixture: {fixture_path}"
    assert schema_path.exists(), f"missing schema: {schema_path}"

    schema = _load_json(schema_path)
    registry = _build_registry(schema_dir)
    validator = Draft202012Validator(schema, registry=registry)

    fixture = _load_json(fixture_path)
    errors = sorted(validator.iter_errors(fixture), key=lambda e: list(e.path))
    assert not errors, (
        f"{fixture_name} failed {schema_name} validation:\n"
        + "\n".join(f"  - {e.message} at {list(e.path)}" for e in errors)
    )


def test_all_fixture_files_covered(fixtures_dir: Path) -> None:
    """Every *.json under tests/fixtures/phase1/ has an entry in the map."""
    on_disk = {p.name for p in fixtures_dir.glob("*.json")}
    mapped = set(FIXTURE_TO_SCHEMA.keys())
    missing_from_map = on_disk - mapped
    missing_on_disk = mapped - on_disk
    assert not missing_from_map, (
        f"fixtures present on disk but not mapped to a schema: {sorted(missing_from_map)}"
    )
    assert not missing_on_disk, (
        f"fixtures mapped to a schema but missing on disk: {sorted(missing_on_disk)}"
    )
