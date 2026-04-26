# ADR-0006: Hebrew + English temporal normalization is deterministic and closed

* Status: Accepted — 2026-04-23
* Context: Phase 3, Wave-1 A4

## Context

Statements reference time in wildly different ways: "in 2024", "בכנסת
ה-25", "last year", "בשנה שעברה", "פברואר 2023". The verdict engine
needs a canonical `TimeScope(start, end, granularity)` to compare
against graph facts.

## Decision

* `civic_temporal.normalize_time_scope(phrase, *, language,
  reference_date=None)` is a pure function: no IO, no LLM, deterministic.
* Supported inputs: ISO dates, bare years, Hebrew month + year,
  Knesset-term references (Hebrew + English), "last year" / "בשנה
  שעברה", "last term" / "הקדנציה הקודמת".
* `civic_temporal.KNESSET_TERMS` is a hand-maintained list of
  (number, start_iso, end_iso) tuples; adding the 26th Knesset is a
  one-line edit.
* Unknown or unparseable phrases return `TimeScope(start=None,
  end=None, granularity="unknown")`. Never raises.

## Alternatives considered

* **LLM-based normalization.** Rejected for the canonical path — an
  LLM is allowed to generate a candidate phrase during decomposition
  (`time_phrase`), but the phrase → scope conversion stays
  deterministic so the same phrase always yields the same scope.
* **`dateparser` / external libraries.** Rejected — the long-tail of
  Hebrew political phrasing isn't covered, and the dependency surface
  isn't worth it when our canonical set is ~20 patterns.

## Consequences

* Granularity is enforced downstream: `vote_cast` and
  `committee_attendance` require non-`unknown` granularity for the
  `checkability` classifier to emit `checkable`.
* When a new phrasing emerges (e.g. fiscal years, semester labels),
  we add a regex + test, not a prompt. Zero training-data concerns.
* The function is safe to run at API request time — no network, no
  disk.
