# ADR-0007: Retrieval reranker is deterministic with fixed weights

* Status: Accepted — 2026-04-23
* Context: Phase 4, Wave-2 B3

## Context

Retrieval returns a mixed bag of graph evidence (structured facts
from Neo4j) and lexical evidence (BM25 / kNN hits from OpenSearch).
The verdict engine needs a single ranked list with a stable order so
the same inputs always produce the same verdict.

## Decision

`civic_retrieval.rerank.rerank(evidence, *, claim_type)` combines
five signals with fixed weights:

| signal                   | weight |
|--------------------------|--------|
| source_tier              | 0.30   |
| directness               | 0.25   |
| temporal_alignment       | 0.20   |
| entity_resolution        | 0.15   |
| cross_source_consistency | 0.10   |

* Weights live in `WEIGHTS` — a module-level dict. Changing a weight
  is a one-commit PR with a matching test update.
* The reranker is pure: same inputs, same order.
* Graph evidence gets a directness boost when `claim_type` matches
  the evidence's `claim_type` (the direct-lookup case). Lexical
  evidence gets a cross-source boost proportional to the number of
  distinct documents that corroborate it.

## Alternatives considered

* **Learned cross-encoder reranker (e.g. ColBERT-v2).** Rejected for
  v1 — we lack the labelled pair data to train it, and a learned
  reranker would defeat the deterministic-verdict invariant. Phase 6
  can revisit.
* **Separate rankers per claim_type.** Rejected — five signals cover
  the whole space, and the per-claim-type divergence lives in which
  evidence the retrievers return, not how we rank it.
* **Allow weights to come from config.** Rejected — `.env`-tunable
  weights made audits harder ("which weights produced this verdict
  last Tuesday?"). Encoded in source; reviewed in git.

## Consequences

* The five-axis `Confidence` rubric in
  `civic_verification.compute_confidence` reuses the same weights
  (imported from `civic_retrieval.rerank.WEIGHTS`). Axis importance
  has one source of truth.
* `RerankScore` carries unweighted axis scores so the verdict engine
  can build the Confidence vector without re-scanning evidence.
* Anyone changing a weight MUST update every test that pins a
  numeric threshold — this is by design.
