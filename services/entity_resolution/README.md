# `civic-entity-resolution`

Deterministic-first entity resolution for civic domain entities
(`person`, `party`, `office`, `committee`, `bill`). Phase 2 ships the
MVP (steps 1-4 of the plan's six-step ladder); steps 5 (fuzzy) and 6
(LLM fallback) land in Phase 3.

Rules-before-LLM is a system-wide invariant (see `docs/AGENT_GUIDE.md`).
This service exists to keep that invariant enforceable.

## Resolution ladder

1. **External ID match** — Look up the upstream canonical ID
   (`knesset_person_id`, `knesset_committee_id`, …) as a Neo4j node
   property. Deterministic; no ambiguity possible.
2. **Exact normalized Hebrew match** — `normalize_hebrew(name)` →
   query Neo4j node's normalized-name property. Niqqud stripped, NFC
   normalized, whitespace collapsed.
3. **Curated alias match** — Look up `entity_aliases` (Phase-2 table,
   migration `0004`). Unique on
   `(entity_kind, alias_text, alias_locale)`. Curated entries are
   reviewer-written (Phase-5 workflow).
4. **Transliteration normalization** — `transliterate_hebrew(name)`
   (deterministic 22-letter table) → repeat step 2/3 against the
   transliteration column.
5. **Fuzzy matching** — `rapidfuzz` comparison against all nodes of
   the target kind. Compares `hebrew_name`, `canonical_name`, and
   `english_name` using `fuzz.ratio`; also applies `fuzz.partial_ratio`
   for Hebrew substring matches (discounted ×0.92 to prevent false
   positives from very short inputs). Thresholds:
   `FUZZY_RESOLVE_THRESHOLD=92`, `FUZZY_MARGIN=5`.
6. **LLM fallback for ties** — Optional `LLMEntityTiebreaker` protocol;
   strictly scoped to resolving ties among > 1 deterministic
   candidates; never creates new facts.

### Pipeline-level fallback (`LiveEntityResolver`)

When the standard 6-step ladder returns `unresolved`, the
`LiveEntityResolver` in `apps/api/src/api/routers/pipeline.py` applies
a CONTAINS-based Cypher fallback:

- Searches across multiple name fields per entity kind (e.g. `title`,
  `hebrew_name`, `canonical_name`, `english_name`).
- Returns the match only when exactly one candidate matches (ambiguous
  multi-matches return `None`).
- Handles partial names like `"הכלכלה"` → `"ועדת הכלכלה"`.

## Public surface

```python
from civic_entity_resolution import (
    normalize_hebrew,
    transliterate_hebrew,
    Candidate,
    ResolveResult,
    resolve,
)

result = resolve(
    kind="person",
    mention_text="אברהם בן דוד",
    external_ids={"knesset_person_id": 12345},
    locale="he",
    neo4j_driver=driver,
    pg_conn=conn,
)
# result.status ∈ {"resolved", "ambiguous", "unresolved"}
# result.canonical_id: UUID | None
# result.candidates: list[Candidate]
# result.method: "external_id" | "exact_he" | "alias" | "transliteration" | None
```

## Ambiguity handling

-   `person`-kind ambiguities write to the Phase-1 `entity_candidates`
    table (`mention_text`, `resolved_person_id`, `confidence`,
    `method`, `evidence`). The Phase-1 schema is person-scoped by
    design; Phase 3 must extend it for the other kinds.
-   Non-`person` ambiguities return `ResolveResult(status="ambiguous")`
    to the caller; the caller may route them to the review workflow
    or defer resolution.

## Gotchas

-   `normalize_hebrew` treats non-breaking space (`\xa0`) as
    whitespace — `str.split()` collapses it. Tests expect the
    collapsed form.
-   The transliteration table is deterministic but intentionally
    lossy (22 consonants, no vowels). It serves as a coarse filter,
    not a round-trip encoding.
-   `entity_aliases` is empty at migration time. Populating it is
    the reviewer's responsibility in Phase 5.
-   `PHASE2_UUID_NAMESPACE` in each adapter must stay stable — every
    resolver match is by business key (UUID5 of the external ID);
    drift creates orphan nodes.
-   **Language detection matters** — `LiveEntityResolver._is_hebrew()`
    routes Hebrew values to `hebrew_name=` and English to
    `english_name=`. Passing English text as `hebrew_name=` will
    silently fail to match anything.
-   **Knesset OData has no English names** — `Person.english_name`
    is unpopulated in the graph (not carried by `KNS_Person`).
    English person names will not resolve until English name data is
    ingested or alias entries are curated.
