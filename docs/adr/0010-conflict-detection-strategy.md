# ADR-0010: Conflicting Tier-1 records → review queue

## Status

Accepted — 2026-04-26

## Context

The plan requires routing Tier-1 disagreements to human review. The
verdict engine already emits a ``mixed`` status when a ``vote_cast``
claim sees multiple distinct recorded values.

## Decision

When ``decide_verdict`` returns ``mixed`` and at least one retrieved
:mod:`RerankScore` chain includes Tier-1 graph evidence, call
:func:`civic_review.conflict.maybe_open_conflict_task` after the
verdict and enqueue a ``review_tasks`` row with ``kind=conflict``.

## Consequences

* Requires a live Postgres handle on :class:`VerifyPipeline`
  (``review_connection=``) — wired in the API lifespan when the stack is
  healthy.
* Does not pre-empt the provenance bundler: tasks are in addition to
  the HTTP response, not a substitute.
