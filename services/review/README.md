# civic-review

Review workflow MVP — the Python surface the Phase-5 reviewer UI will
eventually consume. Routes abstention cases to reviewers, collects
their actions, and preserves a full audit trail.

## Surface

```python
from civic_review import (
    PostgresReviewRepository,
    ReviewAction,
    ReviewActionRecord,
    ReviewTask,
    open_review_task,
)
```

## Allowed actions

One of the five values enumerated in Phase-1 migration 0002's
`review_actions.action` CHECK constraint:

| action    | resulting task status | terminal? |
|-----------|----------------------|-----------|
| approve   | resolved             | yes       |
| reject    | resolved             | yes       |
| relink    | resolved             | yes       |
| annotate  | open                 | no        |
| escalate  | escalated            | yes       |

Terminal tasks still record an audit trail for any attempted
follow-up action — no silent no-ops.

## Atomicity

`PostgresReviewRepository.resolve_task` issues both the `UPDATE
review_tasks` and the `INSERT INTO review_actions` inside the same
transaction. If either step fails the caller sees a rollback.

## Phase 5 handoff

This MVP is intentionally thin. The full reviewer UI + conflict
queue + verdict override UX ships in Phase 5; this package gives
Phase-4 verdicts somewhere to land until then.
