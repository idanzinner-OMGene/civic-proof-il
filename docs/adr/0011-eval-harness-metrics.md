# ADR-0011: Phase-6 eval harness and metric placeholders

## Status

Accepted — 2026-04-26

## Context

The product plan (lines 466-481) lists eight metric families. The
first implementation needs a scriptable entry point before the
stratified gold set is large enough to compute meaningful F1.

## Decision

* Add ``scripts/eval.py`` to iterate ``tests/benchmark/gold_set.yaml``,
  run :meth:`VerifyPipeline.verify` in-process, and write a JSON
  report under ``reports/eval/`` (git-ignored, regenerable).
* Add ``tests/benchmark/config.yaml`` for future numeric gates; initial
  thresholds stay at 0.0 until baseline runs exist.

## Consequences

* CI can invoke ``make eval`` once the benchmark YAML references real
  semantic gold rows and pinned expectations.
* Reports never replace unit tests: they are an ops / research harness.
