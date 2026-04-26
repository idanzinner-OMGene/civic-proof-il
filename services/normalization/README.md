# civic-temporal

Deterministic temporal normalizer for civic-proof-il claim decomposition.

Turns a raw time phrase (Hebrew or English) into a `TimeScope` object
matching `common/time_scope.schema.json`:

```python
from civic_temporal import normalize_time_scope

ts = normalize_time_scope("כנסת ה-25")
# TimeScope(start="2022-11-15T00:00:00+00:00", end=None, granularity="term")
```

## Supported shapes

- ISO-8601 day: `2024-01-15`
- Bare year: `2024`, `ב-2024`
- Hebrew month + year: `ינואר 2024`, `יוני 2023`
- Knesset term: `כנסת ה-25`, `the 25th Knesset`
- Relative-to-reference: `בשנה שעברה`, `last year`, `last term`

Anything else yields `granularity="unknown"` with null bounds — the
checkability classifier converts that to `insufficient_time_scope` for
claim families that require a time anchor (vote_cast, committee_attendance).

Knesset term boundaries live in `knesset_terms.py` (terms 1-25, with
term 25 end open until the term concludes). Sourced from the Knesset's
public session-start dates.
