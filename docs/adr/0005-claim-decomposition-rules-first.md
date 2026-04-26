# ADR-0005: Claim decomposition is rules-first, LLM fallback is schema-validated

* Status: Accepted — 2026-04-23
* Context: Phase 3, Wave-1 A2 + A3

## Context

The verifier turns a free-form political statement into one or more
`AtomicClaim` records. We need decomposition to be (a) deterministic
wherever the language gives us a clean signal and (b) resilient to
paraphrase and unusual phrasing. LLMs are great at paraphrase
recognition but dangerous when we let them write the canonical claim
shape.

## Decision

1. **Rules first.** `services/claim_decomposition/src/civic_claim_decomp/rules.py`
   ships Hebrew and English regex templates for each of the six
   supported `claim_type`s. `decompose(statement, language)` applies
   every template, resolves overlapping spans longest-first, and
   validates every candidate against `civic_ontology.claim_slots.SLOT_TEMPLATES`.
2. **LLM fallback only when rules produce nothing.** If no rule
   matches and an `LLMProvider` was wired, the decomposer calls it
   exactly once per statement. The LLM returns raw slot dicts; each
   dict must pass `validate_slots(claim_type, slots)` OR it is
   discarded. The LLM can NEVER produce a claim shape that bypasses
   the slot templates.
3. **Decomposition NEVER touches the database.** Persistence is a
   separate module (`civic_claim_decomp.persistence.persist_statement`)
   that the API layer calls after decomposition succeeds.

## Alternatives considered

* **LLM-first with a rules sanity check.** Rejected — LLM hallucinates
  slot values for ambiguous sentences and the sanity check can't
  always tell a hallucination from a valid-but-wrong slot.
* **Rules-only, no LLM.** Rejected — the Hebrew corpus is full of
  paraphrase patterns we'd spend years enumerating; we want an escape
  hatch behind strict schema validation.
* **LLM structured output (JSON mode / tool calls).** Still allowed
  inside a provider implementation, but the decomposer doesn't care —
  any provider that conforms to the `LLMProvider` protocol works.

## Consequences

* The decomposer's happy path is provably deterministic — every claim
  produced by rules is traceable back to a named template
  (`source_rule`).
* Adding a new claim family is a two-step process: add a
  `SlotTemplate` + add at least one `RuleTemplate`. The LLM prompt
  card can be updated separately.
* Failure mode visibility: `DecompositionResult` carries
  `rule_matches`, `llm_invoked`, and `validation_errors`; reviewers
  can tell exactly why a claim was dropped.
