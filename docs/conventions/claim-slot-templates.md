# Convention: Claim slot templates

Single source of truth: `packages/ontology/src/civic_ontology/claim_slots.py`.

## Shape

A `SlotTemplate` declares which slots are REQUIRED, OPTIONAL, and
(by exclusion) FORBIDDEN for a given `claim_type`. The set of all
recognised slot names is `ALL_SLOTS`:

```
speaker_person_id, target_person_id, bill_id, committee_id,
office_id, vote_value
```

## Adding a new claim type

1. Add the literal to `ClaimType` in
   `packages/ontology/src/civic_ontology/models/atomic_claim.py`.
2. Add an entry to `SLOT_TEMPLATES` in `claim_slots.py` with
   `required` and `optional` sets.
3. `civic_ontology.schemas.check_schemas` will fail loud if you skip
   step 2 — the drift check cross-checks `SLOT_TEMPLATES` keys
   against the enum.
4. Add at least one `RuleTemplate` in
   `services/claim_decomposition/src/civic_claim_decomp/rules.py`
   (Hebrew + English) so rules-first decomposition emits the new
   type.
5. Add a Cypher template in `infra/neo4j/retrieval/<claim_type>.cypher`
   so graph retrieval has a template to dispatch to.
6. Update `services/verification/src/civic_verification/engine.py`
   `_compare` with the new type's verdict rules.
7. Add a parametrized row to `tests/smoke/test_alignment.py`'s
   `SUPPORTED_CLAIM_TYPES` list.

## Don't

* Don't create `SlotTemplate`s with overlapping required/optional
  sets; the dataclass rejects this at construction time.
* Don't promote a FORBIDDEN slot to OPTIONAL without a migration
  story for existing `AtomicClaim` rows.
* Don't name a new slot outside `ALL_SLOTS`; widen `ALL_SLOTS` first
  in the same commit.
