"""Static alignment audit.

Verifies that every path required by the V1 plan's "Required repo
structure" block (``docs/political_verifier_v_1_plan.md`` lines
163-202) exists, and that the .env / Makefile / compose expose all
expected names. This test is pure-static and runs even without the
docker stack up.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Per docs/political_verifier_v_1_plan.md lines 163-202
REQUIRED_DIRS = [
    "apps/api",
    "apps/worker",
    "apps/reviewer_ui",
    "packages/common",
    "packages/ontology",
    "packages/clients",
    "packages/prompts",
    "infra/docker",
    "infra/migrations",
    "infra/neo4j",
    "infra/opensearch",
    "data_contracts/jsonschemas",
    "services/ingestion/gov_il",
    "services/ingestion/knesset",
    "services/ingestion/elections",
    "services/parsing",
    "services/normalization",
    "services/entity_resolution",
    "services/claim_decomposition",
    "services/retrieval",
    "services/verification",
    "services/review",
    "services/archival",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
    "tests/fixtures",
    "scripts",
    "docs",
]

REQUIRED_FILES = [
    "pyproject.toml",
    ".env.example",
    ".python-version",
    "Makefile",
    "docs/PROJECT_STATUS.md",
    "docs/political_verifier_v_1_plan.md",
    "docs/ARCHITECTURE.md",
    "apps/api/Dockerfile",
    "apps/api/pyproject.toml",
    "apps/worker/Dockerfile",
    "apps/worker/pyproject.toml",
    "apps/migrator/Dockerfile",
    "apps/migrator/pyproject.toml",
    "infra/docker/docker-compose.yml",
    "infra/migrations/alembic.ini",
    "infra/migrations/env.py",
    "infra/migrations/versions/0001_init.py",
    "infra/neo4j/constraints.cypher",
    "infra/opensearch/templates/0001_sources_template.json",
    "scripts/bootstrap-dev.sh",
    "scripts/run-migrations.sh",
    "scripts/seed-demo.sh",
    "scripts/wait-for-services.sh",
]


def test_required_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"missing directories: {missing}"


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"missing files: {missing}"


def test_env_example_has_all_vars():
    text = (ROOT / ".env.example").read_text()
    for var in [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "OPENSEARCH_URL",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET_ARCHIVE",
        "API_HOST",
        "API_PORT",
    ]:
        assert var in text, f"{var} missing from .env.example"


def test_makefile_has_all_targets():
    text = (ROOT / "Makefile").read_text()
    for target in ["up:", "down:", "test:", "smoke:", "seed-demo:", "migrate:"]:
        assert target in text, f"Makefile missing target: {target}"


def test_compose_has_all_services():
    text = (ROOT / "infra/docker/docker-compose.yml").read_text()
    for svc in [
        "postgres",
        "neo4j",
        "opensearch",
        "minio",
        "migrator",
        "api",
        "worker",
    ]:
        assert svc in text, f"compose missing service: {svc}"
