# Ingestion — Knesset (Tier 1)

Five parallel workspace members, one per Knesset entity family:

| Path | Package | OData endpoint | Canonical nodes | Canonical edges |
|---|---|---|---|---|
| `people/` | `civic-ingest-people` | `KNS_Person` / `KNS_PersonToPosition` | `Person`, `Party`, `Office` | `MEMBER_OF`, `HELD_OFFICE` |
| `committees/` | `civic-ingest-committees` | `KNS_Committee` / `KNS_MemberCommittee` | `Committee`, `MembershipTerm` | `MEMBER_OF_COMMITTEE` |
| `votes/` | `civic-ingest-votes` | `KNS_Vote` / `KNS_VoteDetails` | `VoteEvent` | `CAST_VOTE` (→ `Person`, ← `Bill`) |
| `sponsorships/` | `civic-ingest-sponsorships` | `KNS_Bill` / `KNS_BillInitiator` | `Bill` | `SPONSORED` |
| `attendance/` | `civic-ingest-attendance` | `KNS_CmtSessionAttendance` | `AttendanceEvent` | *(ATTENDED edge in Phase 3)* |

Manifests: `services/ingestion/knesset/manifests/<adapter>.yaml`.

Each adapter package is structured identically:

```text
services/ingestion/knesset/<adapter>/
├── pyproject.toml
├── src/civic_ingest_<adapter>/
│   ├── __init__.py
│   ├── parse.py        # OData dict → parser dict
│   ├── normalize.py    # parser dict → Normalized<T> dataclass
│   ├── upsert.py       # Normalized<T> → Neo4j via civic_clients
│   ├── cli.py          # python -m civic_ingest_<adapter> run
│   └── __main__.py
└── tests/
    ├── conftest.py
    └── test_<adapter>.py
```

Unit-test cassettes live at
`tests/fixtures/phase2/cassettes/<adapter>/sample.json`.

## Running an adapter

```bash
# Dry run — fetch + parse + normalize, no writes
uv run python -m civic_ingest_people run --dry-run

# Real run — writes to Postgres (raw_fetch_objects, ingest_runs) and
# Neo4j (Person / Party / Office / edges)
uv run python -m civic_ingest_people run --manifest services/ingestion/knesset/manifests/people.yaml
```

All five adapters share a `--max-pages` flag (default: unlimited)
for first-pass recording and quick smoke runs.

## Identity

-   Business keys are `uuid5(PHASE2_UUID_NAMESPACE,
    "knesset_<kind>:<external_id>")`.
    `PHASE2_UUID_NAMESPACE = 00000000-0000-4000-8000-00000000beef`.
    Do not change this constant.
-   Kind prefixes: `knesset_person`, `knesset_party`, `knesset_office`,
    `knesset_committee`, `knesset_bill`, `knesset_vote`,
    `knesset_attendance_event`, `knesset_membership_term`.
-   Re-running an adapter on the same OData rows is idempotent —
    `MERGE` on the business key in Neo4j, `UNIQUE(content_sha256)` on
    the archive.

## Vote value normalization

`KNS_Vote.Vote` accepts Hebrew (`בעד` / `נגד` / `נמנע`), English
(`for` / `against` / `abstain`), and integer (`1` / `2` / `3`) forms.
The normalizer maps them to the Neo4j canonical strings
(`for` / `against` / `abstain`). Unmapped values are dropped
deterministically (the `CAST_VOTE` upsert template also has a `WHERE
value IN (...)` guard, so either layer's rejection surfaces the same
way).

## Testing

Each adapter's unit tests parse the local cassette, assert the
normalized bundle's shape, and skip the upsert step. The
workspace-wide integration test
(`tests/integration/test_phase2_ingestion.py`) runs all five
adapters end-to-end against a live stack using the same cassettes
via a stub fetcher; it's skipped unless Postgres + Neo4j + MinIO +
OpenSearch are reachable.

## Gotchas

-   `@odata.nextLink` pagination is honored by `iter_odata_pages`;
    do not re-implement pagination inside an adapter.
-   Knesset OData sometimes returns `null` for nullable fields and
    sometimes omits the key entirely. Parsers must handle both.
-   `FirstName` / `LastName` Hebrew fields are Unicode with niqqud
    in older records. `civic_entity_resolution.normalize_hebrew`
    strips niqqud deterministically; do not apply it twice.
-   Attendance captures attendee person UUIDs but does not yet write
    an `ATTENDED` relationship — the template lands in Phase 3.
-   **People manifest covers all historical MKs by design.** The
    `KNS_Person` OData feed is a dimension table (one row per unique
    person ever in the Knesset), so the manifest uses
    `$orderby=PersonID` with no `IsCurrent` filter. This is what
    lets the `coalesce()` back-fill on `person_upsert.cypher`
    attach canonical names to the stub `Person` nodes the votes
    adapter creates for historical-Knesset `CAST_VOTE` endpoints.
    Narrowing the filter here silently turns every vote-stub into
    a permanently nameless Tier-2 node. See
    `PROJECT_STATUS.md` → "Phase 2 — Historical MK coverage".
