# ADR-0003: Postgres-native job queue via `SELECT … FOR UPDATE SKIP LOCKED`

*   **Status:** Accepted
*   **Date:** 2026-04-23
*   **Deciders:** civic-proof-il core team (Phase 2 Wave-A bootstrap)

## Context and Problem Statement

Phase 2 needs a way for the worker (`apps/worker`) to pull ingestion
work units asynchronously: one ingestion run fans out into N page
fetches, each page produces M parse jobs, each parse job feeds one
normalize + one upsert step. The plan
(`docs/political_verifier_v_1_plan.md`) specifies adapters must be
parallelisable, idempotent, and recoverable — meaning at-least-once
delivery with a dead-letter path.

The v1 scope is modest (five adapters × one Knesset term × daily or
weekly cadence). Throughput will stay well under 10 jobs/second for
the foreseeable future. We run exactly one worker replica in
Phase 2 with room to scale to a small handful.

We need a queue that:

1. Delivers jobs at least once, with visibility timeout / claim
   semantics so a crashed worker doesn't lose the job.
2. Supports priority + delayed retry (exponential backoff) + dead
   letters.
3. Doesn't introduce a new backing store in Phase 2 (we already
   operate Postgres, Neo4j, OpenSearch, and MinIO — adding a fifth is
   cost without benefit at this scale).
4. Preserves transactional coupling between "job done" and "side
   effect persisted" so a worker crash after a side effect but before
   marking done either finishes cleanly or is visibly re-tried.
5. Survives the Phase-3 pipeline growth (atomic claim + verification
   + review) without a rewrite.

## Considered Options

1. **Postgres-native queue with `SELECT … FOR UPDATE SKIP LOCKED`**
   (chosen). One `jobs` table, one CTE that locks-and-updates a row
   in one statement. Standard library, zero new infra.
2. **Redis + RQ** (or Celery on Redis). Mature, low-latency, but adds
   a process and makes cross-transaction coupling with Postgres
   awkward.
3. **Celery + RabbitMQ.** Full-featured, but heavyweight for five
   adapters and adds broker ops surface.
4. **Temporal / Airflow / Prefect.** Designed for multi-step
   workflows; the per-job transaction story is excellent. But the
   ops cost is large and the pipeline model forces us to express
   adapters as DAGs prematurely.
5. **`pgmq` / `pg-boss` / `graphile-worker`.** Third-party libraries
   that wrap the same `SKIP LOCKED` pattern. Good, but opinionated on
   schema and add a dependency for logic we can keep under 200 lines
   of our own code.
6. **`LISTEN` / `NOTIFY`-only** (no polling). Lower latency, but no
   durable claim semantics — a missed notification is a lost job.

## Decision Outcome

Chosen option: **Option 1 — hand-rolled Postgres-native queue using
`SELECT … FOR UPDATE SKIP LOCKED` inside a CTE.**

Concretely:

1. **One `jobs` table**, migration `0003_jobs_queue.py`. Columns:
    -   `job_id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
    -   `kind TEXT NOT NULL CHECK (kind IN ('fetch','parse','normalize','upsert'))`
    -   `payload JSONB NOT NULL`
    -   `status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed','dead_letter'))`
    -   `priority SMALLINT NOT NULL DEFAULT 0`
    -   `attempts SMALLINT NOT NULL DEFAULT 0`
    -   `last_error TEXT`
    -   `run_after TIMESTAMPTZ NOT NULL DEFAULT now()`
    -   `ingest_run_id UUID REFERENCES ingest_runs(run_id)`
    -   `created_at`, `updated_at`
    Indexed on `(status, priority DESC, run_after)` to support the
    claim query.
2. **Claim is one statement, one round-trip.** `civic_ingest.queue.claim_one`:

    ```sql
    WITH picked AS (
      SELECT job_id FROM jobs
      WHERE status = 'queued' AND kind = ANY(%s) AND run_after <= now()
      ORDER BY priority DESC, run_after ASC
      FOR UPDATE SKIP LOCKED
      LIMIT 1
    )
    UPDATE jobs SET status = 'running', attempts = attempts + 1,
                    updated_at = now()
    FROM picked WHERE jobs.job_id = picked.job_id
    RETURNING jobs.*;
    ```

    `SKIP LOCKED` guarantees that N concurrent workers never claim
    the same row without any advisory-lock bookkeeping.
3. **Dispatch is decoupled from claim.** `civic_ingest.handlers` is a
   decorator registry: adapters call
   `@handlers.register("fetch", adapter="people")` at import time.
   The worker calls `handlers.dispatch(job)` — adapter-aware lookup
   first, then the generic-kind handler, raising
   `LookupError` if neither exists. This keeps the worker's main loop
   adapter-agnostic and testable with a fake registry.
4. **Success / failure paths** (`mark_done` / `mark_failed`) are
   explicit. `mark_failed` bumps `attempts`, sets `run_after = now() +
   (attempts*attempts) seconds` (exponential backoff), and flips to
   `dead_letter` once `attempts >= max_attempts` (default 5).
5. **Ingest runs wrap batches.** `IngestRun` context manager owns
   `ingest_runs.status` and commits once, at context exit. Within a
   run, individual adapter writes participate in the same
   `psycopg.Connection` transaction; cross-store writes to Neo4j and
   MinIO happen outside the transaction boundary (archival is
   content-addressed and idempotent, Neo4j upserts are `MERGE`-based
   and idempotent).

Rationale: Options 2, 3, and 4 add infra for throughput we don't
have. Option 5 would shrink our code but introduces a third-party
schema we'd have to follow forever. Option 6 sacrifices at-least-once
delivery. Option 1 gets us everything we need in ~200 lines with no
new runtime dependency — and if we outgrow it, the migration path to
`pg-boss` / Temporal is straightforward because our jobs have a
clean, durable schema.

## Consequences

**Positive**

-   Zero new infrastructure. Postgres is already operational;
    `gen_random_uuid()` and `SKIP LOCKED` are supported in our 16.x
    baseline.
-   Jobs and their side effects can share a transaction when it
    matters (e.g. archive + job-done status flip within one `WITH …
    RETURNING`).
-   Priority, backoff, delayed retry, and dead-letter are all
    one-line SQL changes.
-   The worker loop is ~40 lines; nothing to monkey-patch or
    instrument.

**Negative**

-   Polling is at-worst-case O(workers × tick-rate). We default to a
    1-second tick; under sustained load we'll need `LISTEN` /
    `NOTIFY` wakeups (documented in "Known gotchas" in
    `PROJECT_STATUS.md`).
-   Priority arithmetic is limited to `priority SMALLINT`; no
    fairness across adapters beyond what priority lets us express.
    Fine for Phase 2; Phase 3+ may need more.
-   Long-running jobs are vulnerable to worker crashes mid-execution;
    the current design re-claims on the next `run_after` boundary.
    A future visibility-timeout extension (claim heartbeat) would
    help.
-   All workers must share one Postgres — a hard failure of that
    Postgres blocks ingestion. Accepted as a Phase-2 risk because we
    already treat Postgres as a hard dependency of every other path.

## Scope boundaries (what we are NOT deciding here)

-   **Cron scheduling** (triggering the first `queued` row for a
    cadence). Phase 3 will add either a sibling cron container or a
    lightweight scheduler inside the worker.
-   **Fanout topology** (one job vs. one job-per-page). Phase 2
    adapters fan out per-page inside `run_adapter`, so one ingest job
    produces many archive rows but only one worker tick. Phase 3 may
    split this across N workers.
-   **Metrics / observability.** We log structured events via
    `structlog`; Prometheus / OpenTelemetry hooks land in Phase 6
    hardening.

## Related plan and contract references

-   `docs/political_verifier_v_1_plan.md` — ingestion requirements.
-   `infra/migrations/versions/0003_jobs_queue.py` — the schema.
-   `services/ingestion/_common/src/civic_ingest/queue.py` — claim /
    mark-done / mark-failed / enqueue.
-   `services/ingestion/_common/src/civic_ingest/handlers.py` — the
    dispatch registry.
-   `apps/worker/src/worker/main.py` — the worker loop.
