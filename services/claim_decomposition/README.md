# civic-claim-decomp

Rule-first (+ optional LLM fallback) claim decomposition for the
political verifier. Splits a single statement into one or more atomic
claims mapped to the six supported families (plan lines 13-19).

## Surface

```python
from civic_claim_decomp import decompose

result = decompose("John Doe voted against the reform bill in 2024.", "en")
for claim in result.claims:
    print(claim.claim_type, claim.slots, claim.time_phrase)
```

## Pipeline

1. `decompose` runs every ``RuleTemplate`` (see `rules.py`) matching the
   requested language. Longest span wins; ties broken by template order.
2. Every rule match is validated against
   `civic_ontology.claim_slots.validate_slots`. Violations are collected
   into `result.validation_errors`.
3. If zero rule claims pass validation and an `LLMProvider` was
   supplied, the provider is called. Every LLM output is re-validated
   against the slot template before acceptance.
4. The caller is responsible for downstream steps: entity resolution
   (subject text → canonical Person UUID), temporal normalization
   (`time_phrase` → `TimeScope`), checkability classification, and
   persistence.

See `docs/adr/0005-claim-decomposition-rules-first.md` for the design
rationale.

## Gotchas

- **Regex end-anchors are mandatory.** All patterns in `rules.py`
  must end with `\s*\Z`. Without this, lazy quantifiers (`.*?`)
  capture the minimum possible match (often just 2 characters for
  bill/committee/office groups), because trailing groups are optional
  and `finditer` doesn't force expansion. The `\s*\Z` anchor forces
  each lazy group to consume up to end-of-string.
- **Adding new patterns** — follow the existing convention: named
  groups for slots, `\s*\Z` at the end, and test with both short and
  full entity names to ensure the lazy quantifiers expand correctly.
