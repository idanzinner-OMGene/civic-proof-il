# Government Decisions Cassette — Source Record

| Field | Value |
|---|---|
| **Capture URL** | `https://next.obudget.org/search/gov_decisions?q=החלטה+מספר&size=50` |
| **Capture date (UTC)** | 2026-05-04 |
| **SHA-256** | `e7c67cc6fb8a660ec945fb908bfa67fb8fe0482da82b4161ef305b7f26676da5` |
| **Source** | BudgetKey / OpenBudget project — aggregates official government decisions from gov.il |
| **Total indexed records** | 1,971 (filtered for numbered decisions: `q=החלטה+מספר`) |
| **Records in sample** | 50 |
| **First record** | id=`dc13f245-5109-41cd-aa18-f097f1d69bd8`, decision_number=`2084`, publish_date=`2018-02-04T13:30:00`, office=`נציבות שירות המדינה` |

## Re-recording

```bash
curl -s "https://next.obudget.org/search/gov_decisions?q=החלטה+מספר&size=50" \
  -o tests/fixtures/phase2/cassettes/gov_decisions/sample.json
sha256sum tests/fixtures/phase2/cassettes/gov_decisions/sample.json
```

Update the SHA-256 and capture date in this file after re-recording.

## Notes

- The BudgetKey API is maintained by OpenBudget/BudgetKey (open source, GitHub).
- It aggregates government decisions from the official gov.il portal.
- `policy_type` field varies; records with `"החלטות"` in the value are formal cabinet decisions.
- `procedure_number_str` is the official decision number (e.g. "2084", "712", "210/2023").
- `government` field contains the government number as Hebrew text (e.g. "הממשלה ה- 37") or null.
