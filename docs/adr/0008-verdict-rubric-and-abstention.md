# ADR-0008: Verdict rubric + abstention policy are rule-driven and LLM-free

* Status: Accepted — 2026-04-23
* Context: Phase 4, Wave-2 B4 + B5

## Context

The verdict is what gets shown to the citizen and what defines the
project's epistemic posture. The plan's rule (line 31-36) is
unambiguous: LLMs can summarize evidence and draft reviewer
explanations, but they MUST NOT decide whether a claim is supported,
contradicted, or mixed.

## Decision

### Verdict engine

* `civic_verification.engine.decide_verdict(VerdictInputs)` returns a
  `VerdictOutcome(status, confidence, needs_human_review, reasons)`
  where `status ∈ {supported, contradicted, mixed,
  insufficient_evidence, non_checkable}`.
* Dispatch is a Python `match` on `claim_type`:
  * `vote_cast` — graph must have a `vote_value`; recorded value
    mismatch ⇒ contradicted; match ⇒ supported; mixed values ⇒ mixed.
  * `committee_attendance` — if every graph hit has
    `presence='absent'`, contradict; otherwise support.
  * `bill_sponsorship` / `office_held` / `committee_membership` —
    graph match ⇒ support; else ≥1 lexical corroboration ⇒ support;
    else abstain.
  * `statement_about_formal_action` — ≥2 lexical ⇒ support; 1 ⇒
    mixed; 0 ⇒ abstain.

### Abstention thresholds

* `ABSTAIN_OVERALL = 0.45` — below this, status is forced to
  `insufficient_evidence` regardless of the per-claim logic above.
* `HUMAN_REVIEW_OVERALL = 0.62` — below this, we keep the support /
  contradict status but flip `needs_human_review=True`.

### Five-axis confidence rubric

* `compute_confidence(ranked)` takes the MAX across evidence for
  directness / temporal / entity / cross-source and the MAX
  `source_tier` score, then computes `overall` using
  `civic_retrieval.rerank.WEIGHTS`. Axis importance has one source of
  truth (ADR-0007).

### Provenance bundler

* `bundle_provenance(outcome, ranked, ...)` emits the JSON payload
  `/claims/verify` returns. The optional `EvidenceSummarizer` LLM
  seam drafts a reviewer-facing `uncertainty_note` paragraph when
  `needs_human_review=True`. The summarizer CANNOT alter the verdict
  fields; its return value is used verbatim.

## Alternatives considered

* **LLM-scored confidence.** Rejected — the five axes are the
  structural story we want reviewers to audit, and LLM scoring
  couples the verdict to a prompt version.
* **Config-driven thresholds.** Rejected — same argument as ADR-0007.
  Thresholds are in code, reviewed in git.
* **Separate "ambiguous" status instead of mixed.** Rejected — "mixed"
  already captures the case (graph says X, lexical says Y); splitting
  it would just push the decision onto the reviewer UI.

## Consequences

* Every verdict is reconstructible from `(VerdictInputs, WEIGHTS,
  ABSTAIN_OVERALL, HUMAN_REVIEW_OVERALL)` at a given git SHA.
* The LLM failure mode is bounded: a summarizer that returns garbage
  only degrades the `uncertainty_note`; the reviewer still sees the
  deterministic verdict + evidence.
* Threshold changes are high-friction by design (they surface in
  every parametrized test that pins a numeric output).
