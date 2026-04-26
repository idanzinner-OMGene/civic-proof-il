"""Static alignment audit.

Phase 0: verifies that every path required by the V1 plan's
"Required repo structure" block exists and that .env / Makefile /
compose expose all expected names.

Phase 1 (plan lines 204-320): also verifies the canonical data-model
artifacts: the Alembic 0002 migration mentions every Phase-1 table, the
Neo4j constraints file has a CREATE CONSTRAINT for every domain node,
every node + relationship has an upsert template, the three OpenSearch
index templates exist, the JSON Schema + Pydantic surface is complete,
and the archive-URI convention is documented in code + docs.

Pure-static — runs even without the docker stack up.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    "scripts/bootstrap-dev.sh",
    "scripts/run-migrations.sh",
    "scripts/seed-demo.sh",
    "scripts/wait-for-services.sh",
]


# ---- Phase 0 checks -------------------------------------------------------


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
        "reviewer_ui",
    ]:
        assert svc in text, f"compose missing service: {svc}"


# ---- Phase 1: Postgres migration -----------------------------------------

PHASE1_PG_MIGRATION = ROOT / "infra/migrations/versions/0002_phase1_domain_schema.py"

PHASE1_PG_TABLES = [
    "ingest_runs",
    "raw_fetch_objects",
    "parse_jobs",
    "normalized_records",
    "entity_candidates",
    "review_tasks",
    "review_actions",
    "verification_runs",
    "verdict_exports",
]


def test_phase1_pg_migration_exists():
    assert PHASE1_PG_MIGRATION.is_file(), (
        "expected infra/migrations/versions/0002_phase1_domain_schema.py"
    )


@pytest.mark.parametrize("table_name", PHASE1_PG_TABLES)
def test_phase1_pg_migration_mentions_table(table_name: str):
    text = PHASE1_PG_MIGRATION.read_text()
    assert f'"{table_name}"' in text, (
        f"table {table_name!r} not referenced by 0002_phase1_domain_schema.py"
    )


# ---- Phase 1: Neo4j constraints + upsert templates -----------------------

# Each tuple: (neo4j label, upsert-file-snake-case, business-key property on the
# node). The business key is often, but not always, ``<snake>_id`` — e.g.
# ``:SourceDocument`` is keyed on ``document_id`` per plan line 294.
PHASE1_NEO4J_NODES = [
    ("Person", "person", "person_id"),
    ("Party", "party", "party_id"),
    ("Office", "office", "office_id"),
    ("Committee", "committee", "committee_id"),
    ("Bill", "bill", "bill_id"),
    ("VoteEvent", "vote_event", "vote_event_id"),
    ("AttendanceEvent", "attendance_event", "attendance_event_id"),
    ("MembershipTerm", "membership_term", "membership_term_id"),
    ("SourceDocument", "source_document", "document_id"),
    ("EvidenceSpan", "evidence_span", "span_id"),
    ("AtomicClaim", "atomic_claim", "claim_id"),
    ("Verdict", "verdict", "verdict_id"),
]

PHASE1_NEO4J_RELATIONSHIPS = [
    "about_bill",
    "about_person",
    "cast_vote",
    "contradicted_by",
    "evaluates",
    "has_span",
    "held_office",
    "member_of",
    "member_of_committee",
    "sponsored",
    "supported_by",
]

PHASE3_NEO4J_RELATIONSHIPS = PHASE1_NEO4J_RELATIONSHIPS + ["attended"]


@pytest.mark.parametrize("label,snake,key", PHASE1_NEO4J_NODES)
def test_neo4j_constraints_has_node(label: str, snake: str, key: str):
    text = (ROOT / "infra/neo4j/constraints.cypher").read_text()
    needle_label = f":{label})"
    assert needle_label in text, f"constraints.cypher missing label {label!r}"
    assert f"{key} IS UNIQUE" in text, (
        f"constraints.cypher missing unique on {label}.{key}"
    )


@pytest.mark.parametrize("label,snake,key", PHASE1_NEO4J_NODES)
def test_neo4j_upsert_template_exists(label: str, snake: str, key: str):
    path = ROOT / f"infra/neo4j/upserts/{snake}_upsert.cypher"
    assert path.is_file(), f"missing upsert template: {path}"
    text = path.read_text()
    assert f"{key}: ${key}" in text, (
        f"{path.name} must MERGE on the business key {key}"
    )


def test_neo4j_upsert_count():
    files = list((ROOT / "infra/neo4j/upserts").glob("*.cypher"))
    assert len(files) == 12, f"expected 12 node upsert templates, got {len(files)}"


@pytest.mark.parametrize("rel", PHASE3_NEO4J_RELATIONSHIPS)
def test_neo4j_relationship_template_exists(rel: str):
    path = ROOT / f"infra/neo4j/upserts/relationships/{rel}.cypher"
    assert path.is_file(), f"missing relationship template: {path}"


def test_neo4j_relationship_count():
    files = list((ROOT / "infra/neo4j/upserts/relationships").glob("*.cypher"))
    # Phase-1 shipped 11; Phase-3 adds the ATTENDED edge for
    # (:Person)-[:ATTENDED]->(:AttendanceEvent).
    assert len(files) == 12, (
        f"expected 12 relationship templates, got {len(files)}"
    )


# ---- Phase 1: OpenSearch templates ---------------------------------------

PHASE1_OS_TEMPLATES = [
    "0001_source_documents.json",
    "0002_evidence_spans.json",
    "0003_claim_cache.json",
]


@pytest.mark.parametrize("fname", PHASE1_OS_TEMPLATES)
def test_opensearch_template_file_exists(fname: str):
    assert (ROOT / "infra/opensearch/templates" / fname).is_file()


def test_opensearch_templates_are_exactly_three():
    files = sorted(p.name for p in (ROOT / "infra/opensearch/templates").glob("*.json"))
    assert files == PHASE1_OS_TEMPLATES, (
        f"expected exactly {PHASE1_OS_TEMPLATES}, got {files} "
        "(stale placeholder?)"
    )


# ---- Phase 1: JSON Schemas + Pydantic ------------------------------------

PHASE1_JSONSCHEMAS = [
    "atomic_claim.schema.json",
    "verdict.schema.json",
    "evidence_span.schema.json",
    "source_document.schema.json",
    "person.schema.json",
    "office.schema.json",
    "party.schema.json",
    "committee.schema.json",
    "bill.schema.json",
    "vote_event.schema.json",
    "attendance_event.schema.json",
    "membership_term.schema.json",
]

PHASE1_JSONSCHEMAS_COMMON = [
    "source_tier.schema.json",
    "time_scope.schema.json",
    "confidence.schema.json",
]


@pytest.mark.parametrize("fname", PHASE1_JSONSCHEMAS)
def test_jsonschema_file_exists(fname: str):
    assert (ROOT / "data_contracts/jsonschemas" / fname).is_file()


@pytest.mark.parametrize("fname", PHASE1_JSONSCHEMAS_COMMON)
def test_jsonschema_common_file_exists(fname: str):
    assert (ROOT / "data_contracts/jsonschemas/common" / fname).is_file()


PHASE1_ONTOLOGY_MODELS = [
    "atomic_claim.py",
    "attendance_event.py",
    "bill.py",
    "committee.py",
    "evidence_span.py",
    "membership_term.py",
    "office.py",
    "party.py",
    "person.py",
    "source_document.py",
    "verdict.py",
    "vote_event.py",
]


@pytest.mark.parametrize("fname", PHASE1_ONTOLOGY_MODELS)
def test_ontology_model_exists(fname: str):
    assert (
        ROOT / "packages/ontology/src/civic_ontology/models" / fname
    ).is_file()


# ---- Phase 1: docs --------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "docs/DATA_MODEL.md",
        "docs/adr/0001-canonical-data-model.md",
        "docs/conventions/archive-paths.md",
    ],
)
def test_phase1_docs_exist(path: str):
    assert (ROOT / path).is_file(), f"missing {path}"


# ---- Phase 1: civic_clients.archive surface ------------------------------


def test_civic_clients_archive_surface():
    path = ROOT / "packages/clients/src/civic_clients/archive.py"
    assert path.is_file()
    text = path.read_text()
    for symbol in [
        "def build_archive_uri",
        "def parse_archive_uri",
        "def content_sha256",
        "SOURCE_FAMILIES",
    ]:
        assert symbol in text, f"civic_clients/archive.py missing {symbol!r}"


# ---- Phase 1: fixtures ----------------------------------------------------

PHASE1_FIXTURES = [
    "person.json",
    "office.json",
    "membership_term.json",
    "source_document.json",
    "evidence_span.json",
    "atomic_claim.json",
    "verdict.json",
]


@pytest.mark.parametrize("fname", PHASE1_FIXTURES)
def test_phase1_fixture_exists(fname: str):
    assert (ROOT / "tests/fixtures/phase1" / fname).is_file()


# ---- Phase 2: ingestion scaffolding + adapters ----------------------------

PHASE2_ADAPTERS = [
    "people",
    "committees",
    "votes",
    "sponsorships",
    "attendance",
    "positions",
    "bill_initiators",
    "committee_memberships",
]


@pytest.mark.parametrize("adapter", PHASE2_ADAPTERS)
def test_phase2_manifest_exists_for_every_adapter(adapter: str):
    path = ROOT / f"services/ingestion/knesset/manifests/{adapter}.yaml"
    assert path.is_file(), f"missing Phase-2 manifest: {path}"


@pytest.mark.parametrize("adapter", PHASE2_ADAPTERS)
def test_phase2_adapter_package_exists(adapter: str):
    pkg = ROOT / f"services/ingestion/knesset/{adapter}"
    assert (pkg / "pyproject.toml").is_file(), f"missing {pkg}/pyproject.toml"
    assert (
        pkg / f"src/civic_ingest_{adapter}/__init__.py"
    ).is_file(), f"missing civic_ingest_{adapter}/__init__.py"
    for module in ("parse.py", "normalize.py", "upsert.py", "cli.py"):
        assert (
            pkg / f"src/civic_ingest_{adapter}/{module}"
        ).is_file(), f"missing civic_ingest_{adapter}/{module}"


@pytest.mark.parametrize("adapter", PHASE2_ADAPTERS)
def test_phase2_adapter_fixture_exists(adapter: str):
    base = ROOT / f"tests/fixtures/phase2/cassettes/{adapter}"
    candidates = [base / "sample.json", base / "sample.csv"]
    assert any(p.is_file() for p in candidates), (
        f"missing Phase-2 cassette under {base} (expected sample.json or sample.csv)"
    )
    assert (base / "SOURCE.md").is_file(), (
        f"missing SOURCE.md provenance for {adapter} cassette"
    )


PHASE2_PG_MIGRATIONS = [
    "0003_jobs_queue.py",
    "0004_entity_resolution_aliases.py",
]


@pytest.mark.parametrize("fname", PHASE2_PG_MIGRATIONS)
def test_phase2_migration_exists(fname: str):
    assert (ROOT / "infra/migrations/versions" / fname).is_file(), (
        f"missing Phase-2 migration: {fname}"
    )


def test_phase2_jobs_queue_migration_mentions_kinds_and_skip_locked_table():
    text = (ROOT / "infra/migrations/versions/0003_jobs_queue.py").read_text()
    assert '"jobs"' in text, "0003 must create the jobs table"
    for kind in ("fetch", "parse", "normalize", "upsert"):
        assert f"'{kind}'" in text, f"jobs_kind_check missing {kind!r}"
    for status in ("queued", "running", "done", "failed", "dead_letter"):
        assert f"'{status}'" in text, f"jobs_status_check missing {status!r}"


def test_phase2_entity_aliases_migration_mentions_triple_unique():
    text = (
        ROOT / "infra/migrations/versions/0004_entity_resolution_aliases.py"
    ).read_text()
    assert '"entity_aliases"' in text
    assert "uq_entity_aliases_triple" in text


PHASE2_SERVICES = [
    "services/archival/pyproject.toml",
    "services/ingestion/_common/pyproject.toml",
    "services/entity_resolution/pyproject.toml",
]


@pytest.mark.parametrize("path", PHASE2_SERVICES)
def test_phase2_service_package_exists(path: str):
    assert (ROOT / path).is_file(), f"missing Phase-2 service package: {path}"


def test_phase2_source_manifest_schema_exists():
    path = ROOT / "data_contracts/jsonschemas/source_manifest.schema.json"
    assert path.is_file(), "SourceManifest JSON Schema not found"
    text = path.read_text()
    for key in ("family", "adapter", "source_tier", "parser", "cadence_cron"):
        assert f'"{key}"' in text, f"schema missing required field {key!r}"


def test_phase2_workspace_members_registered():
    text = (ROOT / "pyproject.toml").read_text()
    for member in [
        "services/archival",
        "services/ingestion/_common",
        "services/ingestion/knesset/people",
        "services/ingestion/knesset/committees",
        "services/ingestion/knesset/votes",
        "services/ingestion/knesset/sponsorships",
        "services/ingestion/knesset/attendance",
        "services/entity_resolution",
    ]:
        assert member in text, (
            f"workspace pyproject.toml must register {member!r}"
        )


# ---- Phase 2: docs --------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "docs/adr/0002-vcr-record-replay.md",
        "docs/adr/0003-postgres-native-job-queue.md",
        "docs/adr/0004-source-manifest-format.md",
        "docs/conventions/source-manifests.md",
        "docs/conventions/cassette-recording.md",
        "services/archival/README.md",
        "services/ingestion/_common/README.md",
        "services/ingestion/knesset/README.md",
        "services/entity_resolution/README.md",
    ],
)
def test_phase2_docs_exist(path: str):
    assert (ROOT / path).is_file(), f"missing Phase-2 doc: {path}"


def test_phase2_project_status_has_phase2_block():
    text = (ROOT / "docs/PROJECT_STATUS.md").read_text()
    assert "Phase 2" in text, "PROJECT_STATUS.md must mention Phase 2"
    assert "ingestion" in text.lower(), (
        "PROJECT_STATUS.md Phase-2 block must mention ingestion"
    )


def test_phase2_architecture_has_phase2_section():
    text = (ROOT / "docs/ARCHITECTURE.md").read_text()
    assert "Phase 2" in text, "ARCHITECTURE.md must have a Phase 2 section"


# ---- Phase 3: claim decomposition + statement gold set --------------------

PHASE3_SERVICES = [
    "services/claim_decomposition/pyproject.toml",
    "services/normalization/pyproject.toml",
    "services/retrieval/pyproject.toml",
    "services/verification/pyproject.toml",
    "services/review/pyproject.toml",
]


@pytest.mark.parametrize("path", PHASE3_SERVICES)
def test_phase3_service_package_exists(path: str):
    assert (ROOT / path).is_file(), f"missing Phase-3 service package: {path}"


def test_phase3_workspace_members_registered():
    text = (ROOT / "pyproject.toml").read_text()
    for member in [
        "services/claim_decomposition",
        "services/normalization",
        "services/retrieval",
        "services/verification",
        "services/review",
    ]:
        assert member in text, (
            f"workspace pyproject.toml must register {member!r}"
        )


PHASE3_MIGRATIONS = [
    "0005_polymorphic_entity_candidates.py",
    "0006_statements.py",
]


@pytest.mark.parametrize("fname", PHASE3_MIGRATIONS)
def test_phase3_migration_exists(fname: str):
    assert (ROOT / "infra/migrations/versions" / fname).is_file(), (
        f"missing Phase-3 migration: {fname}"
    )


def test_phase3_attended_relationship_exists():
    path = ROOT / "infra/neo4j/upserts/relationships/attended.cypher"
    assert path.is_file(), "Phase-3 must ship the ATTENDED relationship template"


def test_phase3_prompts_cards_exist():
    """All four allowed prompt categories must ship v1 cards (plan line 441)."""

    base = ROOT / "packages/prompts/src/civic_prompts"
    for category in (
        "decomposition",
        "temporal_normalization",
        "summarize_evidence",
        "reviewer_explanation",
    ):
        assert (base / category / "v1.yaml").is_file(), (
            f"missing prompt card for {category}"
        )


def test_phase3_statement_gold_set_structure():
    base = ROOT / "tests/fixtures/phase3"
    assert (base / "statements/README.md").is_file()
    assert (base / "manifests/README.md").is_file()
    assert (base / "manifests/batch_01.jsonl").is_file()
    assert (base / "manifests/semantic_gold_set.jsonl").is_file()


def test_phase3_record_statements_script_exists():
    path = ROOT / "scripts/record-statements.py"
    assert path.is_file(), "missing scripts/record-statements.py"
    text = path.read_text(encoding="utf-8")
    assert "real-data-tests.mdc" in text, (
        "record-statements.py must cite the real-data policy"
    )


# ---- Phase 3 + 4: ontology coverage + retrieval + verification + routers --

SUPPORTED_CLAIM_TYPES = [
    "vote_cast",
    "bill_sponsorship",
    "office_held",
    "committee_membership",
    "committee_attendance",
    "statement_about_formal_action",
]


@pytest.mark.parametrize("claim_type", SUPPORTED_CLAIM_TYPES)
def test_claim_slot_template_registered(claim_type: str) -> None:
    text = (
        ROOT / "packages/ontology/src/civic_ontology/claim_slots.py"
    ).read_text(encoding="utf-8")
    assert f'"{claim_type}"' in text, (
        f"SLOT_TEMPLATES must register {claim_type!r}"
    )


@pytest.mark.parametrize("claim_type", SUPPORTED_CLAIM_TYPES)
def test_graph_retrieval_template_exists(claim_type: str) -> None:
    path = ROOT / "infra/neo4j/retrieval" / f"{claim_type}.cypher"
    assert path.is_file(), f"missing graph retrieval template for {claim_type}"


def test_retrieval_templates_exactly_six() -> None:
    files = sorted(p.name for p in (ROOT / "infra/neo4j/retrieval").glob("*.cypher"))
    expected = sorted(f"{c}.cypher" for c in SUPPORTED_CLAIM_TYPES)
    assert files == expected, (
        f"expected {expected}, got {files} (retrieval template drift)"
    )


def test_retrieval_package_exposes_three_layers() -> None:
    text = (
        ROOT / "services/retrieval/src/civic_retrieval/__init__.py"
    ).read_text(encoding="utf-8")
    for symbol in ("GraphRetriever", "LexicalRetriever", "rerank", "RerankScore"):
        assert symbol in text, f"civic_retrieval must export {symbol!r}"


def test_reranker_exposes_five_weighted_signals() -> None:
    text = (
        ROOT / "services/retrieval/src/civic_retrieval/rerank.py"
    ).read_text(encoding="utf-8")
    for signal in (
        "source_tier",
        "directness",
        "temporal_alignment",
        "entity_resolution",
        "cross_source_consistency",
    ):
        assert signal in text, f"rerank.py must implement {signal!r}"


def test_opensearch_evidence_spans_supports_bm25_and_knn() -> None:
    text = (
        ROOT / "infra/opensearch/templates/0002_evidence_spans.json"
    ).read_text(encoding="utf-8")
    assert "normalized_text" in text, "0002 must expose normalized_text for BM25"
    assert "knn_vector" in text, "0002 must expose knn_vector embedding for vector search"


def test_verification_module_exposes_engine_and_rubric() -> None:
    text = (
        ROOT / "services/verification/src/civic_verification/__init__.py"
    ).read_text(encoding="utf-8")
    for symbol in (
        "decide_verdict",
        "compute_confidence",
        "bundle_provenance",
        "UncertaintyBundler",
    ):
        assert symbol in text, f"civic_verification must export {symbol!r}"


def test_verdict_abstention_thresholds_declared() -> None:
    text = (
        ROOT / "services/verification/src/civic_verification/engine.py"
    ).read_text(encoding="utf-8")
    for needle in ("ABSTAIN_OVERALL", "HUMAN_REVIEW_OVERALL"):
        assert needle in text, f"verdict engine must declare {needle}"


@pytest.mark.parametrize(
    "router_module", ["claims.py", "persons.py", "review.py", "pipeline.py"]
)
def test_phase4_api_router_module_exists(router_module: str) -> None:
    assert (ROOT / "apps/api/src/api/routers" / router_module).is_file()


def test_phase4_api_main_wires_all_three_routers() -> None:
    text = (ROOT / "apps/api/src/api/main.py").read_text(encoding="utf-8")
    for router in ("claims_router", "persons_router", "review_router"):
        assert router in text, f"api/main.py must include {router}"


def test_phase4_api_pyproject_declares_pipeline_deps() -> None:
    text = (ROOT / "apps/api/pyproject.toml").read_text(encoding="utf-8")
    for dep in (
        "civic-claim-decomp",
        "civic-temporal",
        "civic-retrieval",
        "civic-verification",
        "civic-entity-resolution",
    ):
        assert dep in text, f"apps/api must depend on {dep}"


def test_phase3_prompt_loader_exposes_load_card() -> None:
    text = (
        ROOT / "packages/prompts/src/civic_prompts/__init__.py"
    ).read_text(encoding="utf-8")
    assert "load_card" in text, "civic_prompts must expose load_card()"


def test_phase3_statement_persistence_migration_defines_both_tables() -> None:
    text = (
        ROOT / "infra/migrations/versions/0006_statements.py"
    ).read_text(encoding="utf-8")
    for table in ("statements", "statement_claims"):
        assert f'"{table}"' in text, f"0006 must create {table!r}"


def test_phase3_polymorphic_entity_candidates_migration_has_entity_kind() -> None:
    text = (
        ROOT / "infra/migrations/versions/0005_polymorphic_entity_candidates.py"
    ).read_text(encoding="utf-8")
    assert "entity_kind" in text, "0005 must add entity_kind column"
    assert "canonical_entity_id" in text, (
        "0005 must rename resolved_person_id to canonical_entity_id"
    )


def test_entity_resolution_uses_rapidfuzz() -> None:
    text = (
        ROOT / "services/entity_resolution/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert "rapidfuzz" in text, "entity_resolution must depend on rapidfuzz"


def test_entity_resolver_exposes_fuzzy_and_tiebreaker() -> None:
    text = (
        ROOT / "services/entity_resolution/src/civic_entity_resolution/__init__.py"
    ).read_text(encoding="utf-8")
    for symbol in ("FUZZY_RESOLVE_THRESHOLD", "FUZZY_MARGIN", "LLMEntityTiebreaker"):
        assert symbol in text, f"civic_entity_resolution must export {symbol!r}"


def test_claim_decomposition_exposes_decompose_and_checkability() -> None:
    text = (
        ROOT / "services/claim_decomposition/src/civic_claim_decomp/__init__.py"
    ).read_text(encoding="utf-8")
    assert "decompose" in text, "civic_claim_decomp must expose decompose()"


def test_temporal_normalizer_exposes_knesset_terms() -> None:
    text = (
        ROOT / "services/normalization/src/civic_temporal/__init__.py"
    ).read_text(encoding="utf-8")
    for symbol in ("normalize_time_scope", "KNESSET_TERMS"):
        assert symbol in text, f"civic_temporal must export {symbol!r}"


# ---- Gold-set label pinning -----------------------------------------------


def _iter_statement_fixtures() -> list[Path]:
    base = ROOT / "tests/fixtures/phase3/statements"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir()]


def test_gold_set_statements_have_pinned_labels() -> None:
    """Every recorded statement gold-set item must ship statement.txt +
    SOURCE.md (real-data provenance) + labels.yaml (the pinned expected
    decomposition + checkability tags).
    """

    missing: list[str] = []
    for entry in _iter_statement_fixtures():
        for fname in ("statement.txt", "SOURCE.md", "labels.yaml"):
            if not (entry / fname).is_file():
                missing.append(f"{entry.name}/{fname}")
    assert not missing, (
        "gold-set label drift — every statement folder needs "
        f"statement.txt + SOURCE.md + labels.yaml; missing: {missing}"
    )


PLACEHOLDER_NEEDLES = [
    "example.com",
    "00000000-0000-4000-8000-",
    "\"PersonID\": 30800",
    "'PersonID': 30800",
    "Benjamin Netanyahu",
    "Sample body content",
    "sample evidence text",
    "Bill X \u2014 Sample Legislation",
    "abc123abc123abc123abc123",
    "בני גנץ",
]


def _scan_fixture_dir(directory: Path) -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".csv"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for needle in PLACEHOLDER_NEEDLES:
            if needle in text:
                hits.append((path, needle))
    return hits


# ---- Phase 5 + 6: review extensions + eval / regression scripts -------------


def test_phase5_review_modules_exist() -> None:
    base = ROOT / "services/review/src/civic_review"
    for name in ("conflict.py", "correction.py", "evidence.py"):
        assert (base / name).is_file(), f"missing {name}"


def test_phase5_review_endpoints_in_router() -> None:
    text = (ROOT / "apps/api/src/api/routers/review.py").read_text(encoding="utf-8")
    for needle in ("/relink-entity", "/confirm-evidence", "_get_pg_connection"):
        assert needle in text, f"review router must mention {needle!r}"


def test_reviewer_ui_package_has_entrypoint() -> None:
    p = ROOT / "apps/reviewer_ui/src/reviewer_ui/main.py"
    assert p.is_file()
    t = p.read_text(encoding="utf-8")
    assert "Jinja2Templates" in t and "create_app" in t


def test_phase6_scripts_exist() -> None:
    for rel in ("scripts/eval.py", "scripts/freshness_check.py", "scripts/index_evidence.py"):
        assert (ROOT / rel).is_file()


def test_phase6_benchmark_config_exists() -> None:
    assert (ROOT / "tests/benchmark/gold_set.yaml").is_file()
    assert (ROOT / "tests/benchmark/config.yaml").is_file()


def test_phase6_regression_tests_present() -> None:
    for rel in (
        "tests/regression/test_verdict_provenance.py",
        "tests/regression/test_provenance_complete.py",
    ):
        assert (ROOT / rel).is_file()


def test_no_synthetic_placeholders_in_fixtures():
    """Forbid hand-invented domain data in tests/fixtures/**.

    See ``.cursor/rules/real-data-tests.mdc``: every fixture byte must
    trace to a real upstream recording. If any of these telltale
    placeholder strings appear, regenerate the fixture from a real
    cassette instead of hand-editing.
    """

    hits = _scan_fixture_dir(ROOT / "tests/fixtures")
    assert not hits, (
        "forbidden synthetic placeholder(s) in tests/fixtures (see "
        ".cursor/rules/real-data-tests.mdc):\n"
        + "\n".join(f"  {p.relative_to(ROOT)} :: {needle!r}" for p, needle in hits)
    )
