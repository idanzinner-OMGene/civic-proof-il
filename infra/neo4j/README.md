# Neo4j — domain schema, constraints, and upsert templates

This directory owns the Neo4j schema for the political verifier. It contains:

- `constraints.cypher` — all node unique + existence constraints, applied by the
  migrator on every boot via `scripts/run-migrations.sh` (which streams the file
  through `cypher-shell`).
- `init.cypher` — Phase-0 smoke script; leaves a single `ok = 1` row. Useful to
  verify `cypher-shell` connectivity against a running container.
- `upserts/` — parameterized `MERGE` templates. One file per node, plus
  `upserts/relationships/` with one file per relationship.

## Files

### Constraints

- `constraints.cypher` — 12 node unique constraints + 12 node
  property-existence constraints (24 `CREATE CONSTRAINT` statements total),
  covering every node listed in `docs/political_verifier_v_1_plan.md`
  lines 204-217:
  Person, Party, Office, Committee, Bill, VoteEvent, AttendanceEvent,
  MembershipTerm, SourceDocument, EvidenceSpan, AtomicClaim, Verdict.

### Node upsert templates (`infra/neo4j/upserts/`)

One file per node, each `MERGE`-ing on the business key with an
`ON CREATE SET` / `ON MATCH SET` block and returning the key:

- `person_upsert.cypher`
- `party_upsert.cypher`
- `office_upsert.cypher`
- `committee_upsert.cypher`
- `bill_upsert.cypher`
- `vote_event_upsert.cypher`
- `attendance_event_upsert.cypher`
- `membership_term_upsert.cypher`
- `source_document_upsert.cypher`
- `evidence_span_upsert.cypher`
- `atomic_claim_upsert.cypher`
- `verdict_upsert.cypher`

### Relationship upsert templates (`infra/neo4j/upserts/relationships/`)

One file per relationship in `docs/political_verifier_v_1_plan.md`
lines 219-230. Each `MATCH`es both endpoints on their business keys and
`MERGE`s the relationship:

- `member_of.cypher` — `(:Person)-[:MEMBER_OF {valid_from, valid_to}]->(:Party)`
- `held_office.cypher` — `(:Person)-[:HELD_OFFICE {valid_from, valid_to}]->(:Office)`
- `member_of_committee.cypher` — `(:Person)-[:MEMBER_OF_COMMITTEE {valid_from, valid_to}]->(:Committee)`
- `sponsored.cypher` — `(:Person)-[:SPONSORED]->(:Bill)`
- `cast_vote.cypher` — `(:Person)-[:CAST_VOTE {value}]->(:VoteEvent)`
  where `value ∈ {'for','against','abstain'}`
- `has_span.cypher` — `(:SourceDocument)-[:HAS_SPAN]->(:EvidenceSpan)`
- `about_person.cypher` — `(:AtomicClaim)-[:ABOUT_PERSON]->(:Person)`
- `about_bill.cypher` — `(:AtomicClaim)-[:ABOUT_BILL]->(:Bill)`
- `supported_by.cypher` — `(:AtomicClaim)-[:SUPPORTED_BY]->(:EvidenceSpan)`
- `contradicted_by.cypher` — `(:AtomicClaim)-[:CONTRADICTED_BY]->(:EvidenceSpan)`
- `evaluates.cypher` — `(:Verdict)-[:EVALUATES]->(:AtomicClaim)`

## Upsert convention

**All writes to Neo4j must go through one of these templates.** No ad-hoc
`CREATE` or inline `MERGE` in application code. Benefits:

1. **Idempotent.** Every template keys on the business key (UUID4) and uses
   `ON CREATE SET` / `ON MATCH SET`. Re-running the same call does not duplicate
   nodes or overwrite values with nulls.
2. **Null-safe updates.** Scalar properties on update use
   `coalesce($param, node.param)` so missing fields preserve existing values
   instead of wiping them.
3. **Typed timestamps.** ISO-8601 strings passed as params are coerced with
   `datetime(...)` inside the template, matching the Phase-1 contract
   (Postgres `TIMESTAMPTZ` → Neo4j `datetime()` → OpenSearch `date`).
4. **Consistent audit fields.** Every node gets `created_at` on insert and
   `updated_at` on update.
5. **Single source of truth.** If the shape of a node changes, there is one
   file to edit, and migrations can be written as parameterized runs of the
   same template.

### Relationship-property existence — Community-edition caveat

Neo4j 5 Community **does not support relationship-property existence
constraints** (`CREATE CONSTRAINT ... FOR ()-[r:TYPE]-() REQUIRE r.prop IS NOT NULL`
is Enterprise-only). For the relationships where the plan declares required
properties (`MEMBER_OF.valid_from`, `HELD_OFFICE.valid_from`,
`MEMBER_OF_COMMITTEE.valid_from`, `CAST_VOTE.value`) we therefore enforce
existence **inside the upsert templates**:

- The template filters with `WHERE <prop> IS NOT NULL` before the `MERGE`, so a
  call missing the required property is a no-op rather than producing a
  half-formed edge.
- `cast_vote.cypher` also restricts `value` to the enum
  `{'for', 'against', 'abstain'}`.

If and when we upgrade to Enterprise, these filters can be replaced with real
relationship-existence constraints, and the templates kept for ergonomics
(idempotency + audit fields).

## Usage

Writes go through `civic_clients.neo4j.run_upsert` (owned by Agent E). The
helper loads a template file from `infra/neo4j/upserts/` and executes it with
the given parameters:

```python
from civic_clients.neo4j import run_upsert

run_upsert(
    "infra/neo4j/upserts/person_upsert.cypher",
    {
        "person_id": "11111111-1111-4111-8111-111111111111",
        "canonical_name": "Plony Almony",
        "hebrew_name": "פלוני אלמוני",
        "english_name": "Plony Almony",
        "external_ids": '{"knesset_id": "12345"}',
        "source_tier": 1,
    },
)

run_upsert(
    "infra/neo4j/upserts/relationships/held_office.cypher",
    {
        "person_id": "11111111-1111-4111-8111-111111111111",
        "office_id": "22222222-2222-4222-8222-222222222222",
        "valid_from": "2022-12-29T00:00:00Z",
        "valid_to": None,
    },
)
```

Every call is idempotent — running the same params a second time updates
`updated_at` but does not duplicate nodes or edges.

## Smoke test

```bash
docker compose -f infra/docker/docker-compose.yml exec -T neo4j \
  cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < infra/neo4j/init.cypher
```

Expect a single row: `ok = 1`.

## Local Neo4j workflow

Two dev Neo4j instances exist; they share host port `7687` and **must not run
simultaneously**:

1. **Compose Neo4j** (`docker-compose.yml` service `neo4j`, image `neo4j:5-community`)
   — ephemeral, wiped on every `make down -v`, rebuilt on every `make up`.
   Owns the automated test path: the migrator streams
   `constraints.cypher` into it and `tests/integration/test_phase1_persistence.py`
   writes / reads / tears down fixture data through it. Credentials come from
   the repo-root `.env` (`NEO4J_USER`, `NEO4J_PASSWORD`).
2. **Local Neo4j** (Homebrew `neo4j` service or Neo4j Desktop on
   `bolt://localhost:7687`) — persistent, browsable dataset for manual
   inspection. Credentials come from `.cursor/.env` (`G_DB_CONNECTION_STRING`,
   `G_DB_USER`, `G_DB_PASSWORD`, optional `G_DB_NAME`).

### Loading Phase-1 fixtures into the local Neo4j

Use `scripts/neo4j_load_phase1_local.py` to wipe the local instance and load a
clean, complete Phase-1 reference dataset. It is deliberately standalone
(parses `.cursor/.env` directly, does not import `civic_common.Settings` or
`civic_clients`) so it runs without the rest of the stack configured.

```bash
# Make sure the compose Neo4j is NOT running (it would collide on port 7687).
make down                  # if the compose stack is up
brew services stop neo4j   # only if you need to restart your local Neo4j

# Start your local Neo4j.
brew services start neo4j
# ...or open Neo4j Desktop and start your project.

# Run the loader.
uv run python scripts/neo4j_load_phase1_local.py
```

The loader:

1. Parses `.cursor/.env` and connects to the bolt URI listed under `G_DB_*`.
2. `DETACH DELETE`s every node + relationship (batched in transactions of
   10,000 rows).
3. Drops every existing constraint and every non-`LOOKUP` index (the two
   system `LOOKUP` indexes cannot be dropped and are preserved).
4. Re-applies `infra/neo4j/constraints.cypher` (12 unique constraints).
5. Upserts all 12 Phase-1 fixture nodes using the templates under
   `infra/neo4j/upserts/` (Person, Party, Office, Committee, Bill, VoteEvent,
   AttendanceEvent, MembershipTerm, SourceDocument, EvidenceSpan, AtomicClaim,
   Verdict).
6. Merges all 11 Phase-1 relationships using the templates under
   `infra/neo4j/upserts/relationships/` (about_bill, about_person, cast_vote,
   contradicted_by, evaluates, has_span, held_office, member_of,
   member_of_committee, sponsored, supported_by). Deterministic params:
   `valid_from/valid_to` for temporal rels come from `membership_term.json`,
   `cast_vote.value` is hard-coded `"for"`.
7. Verifies label counts (one per label) and relationship counts (one per
   type), printing both tables.

Re-running is safe — the wipe step is destructive by design, so any ad-hoc
experiments in the same DB will be erased. Inspect the loaded graph at
<http://localhost:7474> with the same `G_DB_USER` / `G_DB_PASSWORD`.

### When to use which instance

- Writing / running automated tests for the data model → compose Neo4j
  (wiped on every run, matches CI).
- Exploring the Phase-1 graph in Browser, querying by hand, sanity-checking
  new rel patterns before they land in an upsert template → local Neo4j with
  `scripts/neo4j_load_phase1_local.py`.
- Ingesting real Phase-2 data → TBD (compose Neo4j for now; a managed
  instance will appear later in the roadmap).
