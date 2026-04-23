# `civic-ingest` — shared ingestion primitives

Cross-adapter machinery shared by every `services/ingestion/<family>/
<adapter>/` package. Adapter authors consume this library; they do
not re-implement its primitives.

## Public surface

```python
from civic_ingest import (
    # Manifests
    SourceManifest, EntityHints, load_manifest, load_all_manifests,
    # OData helpers
    ODataPage, parse_odata_page, iter_odata_pages,
    # Adapter runner
    AdapterResult, run_adapter,
    # Postgres-native queue
    Job, enqueue, claim_one, mark_done, mark_failed,
    # Ingest runs
    IngestRun,
    # Handler registry
    register, dispatch,
)
```

## Modules

-   **`manifest`** — Pydantic `SourceManifest` (kept in lockstep with
    `data_contracts/jsonschemas/source_manifest.schema.json`) and
    loaders. See `docs/conventions/source-manifests.md`.
-   **`odata`** — Knesset OData V4 JSON helpers. `ODataPage`
    dataclass, `parse_odata_page(json_dict)`, and
    `iter_odata_pages(fetch, url)` that follows `@odata.nextLink`.
-   **`adapter`** — The runner. `run_adapter(manifest, fetch, archive,
    parse, normalize, upsert)` orchestrates fetch → archive →
    parse → normalize → upsert per page. Plug your adapter's four
    callables in, get back an `AdapterResult` with page / row counts.
-   **`queue`** — Postgres-native job queue using
    `SELECT … FOR UPDATE SKIP LOCKED`. `enqueue(conn, kind, payload,
    …)` → job_id; `claim_one(conn, kinds)` → `Job | None`;
    `mark_done(conn, job_id)`; `mark_failed(conn, job_id, error=…,
    max_attempts=…)`. See ADR-0003.
-   **`orchestrator`** — `IngestRun(source_family)` context manager.
    Owns the `ingest_runs` row for the duration of the `with` block,
    commits `succeeded` or `failed` on exit.
-   **`handlers`** — Decorator registry for job kinds.
    `@register("fetch", adapter="people")` on your handler function;
    the worker's main loop calls `dispatch(job)`.

## Gotchas

-   **`run_adapter` runs the fetch loop in-process.** It does not
    enqueue sub-jobs; one `IngestRun` → one adapter invocation →
    many pages fetched serially. Parallelising pages is a Phase-3
    concern.
-   **`IngestRun.__exit__` commits or rolls back based on the raised
    exception.** Do not call `conn.commit()` inside the block unless
    you are recording a known-good intermediate state; a premature
    commit defeats the "atomic archive + status" contract.
-   **`claim_one`'s CTE updates `attempts += 1` eagerly.** If your
    handler crashes before `mark_done`, the incremented attempt count
    is already visible — `mark_failed` then respects the new count
    for backoff / dead-letter logic.
-   **Manifest validation happens at load time, not import time.**
    An adapter module can be imported even if its manifest is
    broken; the error surfaces on first `load_manifest` call.

## Testing hygiene

-   `tests/` has no `__init__.py`; test filenames are unique across
    adapters to avoid pytest rootdir collisions.
-   Unit tests use fakes for `psycopg.Connection` and the Neo4j
    driver; integration tests go through the real stack behind
    `@pytest.mark.integration`.
