"""Shared fixtures for civic-ontology tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repo root (…/civic-proof-il)."""
    # tests/ -> packages/ontology/ -> packages/ -> repo root
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def schema_dir(repo_root: Path) -> Path:
    return repo_root / "data_contracts" / "jsonschemas"


@pytest.fixture(scope="session")
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures" / "phase1"
