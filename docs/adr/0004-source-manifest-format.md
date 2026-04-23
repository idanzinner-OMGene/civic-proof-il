# ADR-0004: Source manifest format (YAML + Pydantic + JSON Schema)

*   **Status:** Accepted
*   **Date:** 2026-04-23
*   **Deciders:** civic-proof-il core team (Phase 2 Wave-A bootstrap)

## Context and Problem Statement

Phase 2 onboards five Knesset ingestion adapters in parallel, and the
plan (`docs/political_verifier_v_1_plan.md`) anticipates many more
adapters across gov.il, election results, and Tier-2 contextual
sources. Each adapter needs a machine-readable declaration of:

-   Which **source family** it belongs to (`knesset` / `gov_il` /
    `elections`) — anchors the archive path convention
    (`conventions/archive-paths.md`).
-   Which **adapter kind** it is (`people` / `committees` / `votes` /
    …) — drives the job-handler dispatch registry.
-   The **source URL** it fetches from.
-   The **trust tier** (1 / 2 / 3) — enforced by the verification
    layer (Tier 1 is canonical; Tier 3 is discovery-only).
-   The **parser kind** (`odata_v4_json` / `html` / `pdf` / `csv` / …)
    — selects the deserializer.
-   The **cadence** (cron expression) — informs scheduling and
    freshness monitoring.
-   **Entity hints** — which Neo4j node kinds / relationships the
    adapter is allowed to write to.

We need a single, well-typed representation that:

1. Humans can read and hand-edit (reviewers will onboard adapters).
2. Adapters can load at runtime without importing adapter-specific
   Python.
3. Static audits can validate without running any code.
4. Stays in lockstep with the Pydantic model and the JSON Schema
   (Phase-1 Agent-D decision: hand-written JSON Schemas are canonical
   + Pydantic models are the typed surface).

## Considered Options

1. **YAML files + Pydantic `SourceManifest` + hand-written JSON
   Schema** (chosen). One file per adapter under
   `services/ingestion/<family>/manifests/<name>.yaml`; the Pydantic
   model is loaded at runtime; the JSON Schema is referenced by the
   static alignment audit.
2. **TOML files.** Python-native, comment support, but YAML has
   better multi-line list ergonomics for `entity_hints` and lower
   developer friction (reviewers will edit these; YAML is more
   familiar outside the Python world).
3. **JSON files** (the schema's own format). Zero parser risk, but no
   comments and awkward for multi-line entries.
4. **Python modules** (`manifest.py` per adapter, exporting a
   `SourceManifest` instance). Type-safe by construction, but code
   review conflates "Python config" with "Python logic" and encourages
   drift (people start importing things).
5. **Single root `manifests.yaml`** with one entry per adapter.
   Simpler to glob-load; harder to review per-adapter PRs (merge
   conflicts on every adapter change).

## Decision Outcome

Chosen option: **Option 1 — YAML files + Pydantic `SourceManifest` +
hand-written JSON Schema.**

Concretely:

1. **One YAML file per adapter** at
   `services/ingestion/<family>/manifests/<name>.yaml`. The full
   Phase-2 set lives under `services/ingestion/knesset/manifests/`.
2. **`civic_ingest.manifest.SourceManifest`** (Pydantic v2,
   `model_config = ConfigDict(extra="forbid", populate_by_name=True)`)
   is the runtime surface. `load_manifest(path)` reads the YAML,
   validates it, returns a model instance. `load_all_manifests(root)`
   walks the manifest tree.
3. **`data_contracts/jsonschemas/source_manifest.schema.json`
   (Draft 2020-12)** is the contract artifact. Static alignment audit
   (`tests/smoke/test_alignment.py`) checks the schema exists,
   declares the expected fields (`family`, `adapter`, `source_url`,
   `source_tier`, `parser`, `cadence_cron`), and matches the Pydantic
   model's field set.
4. **Adapters never hard-code their manifest.** Each adapter CLI
   (`python -m civic_ingest_<name> run`) takes `--manifest` (default:
   `services/ingestion/knesset/manifests/<name>.yaml`). The worker's
   dispatch path reads the manifest by adapter name.
5. **Source tier and parser kind are closed enums.** `source_tier ∈
   {1, 2, 3}` (enforced by `Literal[1, 2, 3]`), `parser ∈
   {odata_v4_json, html, pdf, csv, json}`. New values require a PR
   to the model + schema, not a config-only change, so the
   verification layer's Tier-1 rules remain discoverable.

Rationale: Option 2 (TOML) is a reasonable alternative but YAML's
multi-line list ergonomics win for `entity_hints`. Option 3 loses
comments, which matters for cadence expressions that deserve inline
explanation. Option 4 (Python modules) breaks the "config vs code"
boundary and encourages drift. Option 5 (single root) doesn't
survive PR-level review granularity as the adapter count grows.

## Consequences

**Positive**

-   New adapters onboard with a YAML PR + a package skeleton; no
    model change needed.
-   Manifest validation errors surface at adapter boot (Pydantic) and
    at CI audit time (JSON Schema + static alignment test).
-   Review-friendly: each manifest is < 20 lines of YAML, fits on
    one screen, and reads like plain English.

**Negative**

-   Two artifacts to keep in sync (Pydantic model + JSON Schema).
    Mitigation: the static alignment audit diffs field sets; the
    Phase-1 Agent-D convention (hand-written schema + Pydantic as
    typed surface, drift checked by CI) already lives here.
-   YAML accepts duck-typed values that Pydantic may coerce silently
    (e.g. `cadence_cron: 0 3 * * *` parses as a string, but a naive
    author could write `0 3 * * *` → list). `SourceManifest` declares
    `cadence_cron: str`; Pydantic will fail fast on non-string values.
-   No runtime validation of `cadence_cron` as a valid cron
    expression. Phase 3 adds a cron parser; for Phase 2 we only type
    it as string.

## Scope boundaries (what we are NOT deciding here)

-   **Cron scheduling.** Scheduler ownership is deferred to Phase 3.
-   **Manifest versioning.** No version field today; manifests are
    read by their current Pydantic model. When the model changes
    incompatibly we'll introduce `schema_version`.
-   **Secrets.** No manifest contains credentials. When we add an
    authenticated source, credentials go through `civic_common.settings`,
    not the manifest.

## Related plan and contract references

-   `docs/political_verifier_v_1_plan.md` — ingestion adapter
    responsibilities and source-tier rules.
-   `docs/conventions/source-manifests.md` — operational runbook and
    field-by-field semantics.
-   `services/ingestion/_common/src/civic_ingest/manifest.py` —
    Pydantic model + loaders.
-   `data_contracts/jsonschemas/source_manifest.schema.json` —
    Draft 2020-12 schema.
-   `services/ingestion/knesset/manifests/*.yaml` — the five
    Phase-2 manifests.
