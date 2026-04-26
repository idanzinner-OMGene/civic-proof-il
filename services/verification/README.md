# civic-verification

Deterministic verdict engine, abstention policy, five-axis confidence
rubric, and provenance bundler for the Phase-4 `/claims/verify` slice.

## Surface

```python
from civic_verification import (
    VerdictInputs, VerdictOutcome, decide_verdict,
    compute_confidence, bundle_provenance, UncertaintyBundler,
)
```

## Pipeline

1. `decide_verdict(VerdictInputs)` — takes the resolved atomic claim +
   reranked evidence list + checkability tag and returns a
   `VerdictOutcome` with status, confidence vector, and
   `needs_human_review` flag.
2. `compute_confidence(ranked)` — applies the five-axis rubric using
   the SAME weights the reranker exposes via
   `civic_retrieval.rerank.WEIGHTS` so axis importance has a single
   source of truth.
3. `bundle_provenance(outcome, ranked, ...)` — packs the verdict and
   top-k evidence into a stable JSON payload.  The optional
   `EvidenceSummarizer` protocol is the ONLY LLM seam in verification
   — it drafts a reviewer-facing `uncertainty_note` paragraph and can
   never alter the verdict fields.

## Status mapping

| claim_type                      | supports                          | contradicts                     |
|---------------------------------|-----------------------------------|---------------------------------|
| `vote_cast`                     | graph match on `vote_value`       | recorded value ≠ expected       |
| `bill_sponsorship`              | graph match OR lexical corrob.    | n/a (abstains)                  |
| `office_held`                   | graph match OR lexical corrob.    | n/a (abstains)                  |
| `committee_membership`          | graph match OR lexical corrob.    | n/a (abstains)                  |
| `committee_attendance`          | `presence='present'` in graph     | `presence='absent'` only        |
| `statement_about_formal_action` | ≥2 lexical corroborations         | 1 source → `mixed`              |

## Abstention knobs

`ABSTAIN_OVERALL=0.45`, `HUMAN_REVIEW_OVERALL=0.62`. Below the first
threshold we emit `insufficient_evidence`; below the second we still
set `needs_human_review=True` even on a support/contradict outcome.
