# Parsing service

> **v2 placeholder.** This service is out of scope for v1 (Knesset-only). The v1 pipeline uses the parsers bundled inside each ingestion adapter (`services/ingestion/knesset/<name>/src/.../parse.py`). A dedicated cross-family parsing service is planned for v2 to handle HTML / PDF artifacts from gov.il and election sources.

Transforms raw archived artifacts (HTML, PDF, JSON, CSV, text) into normalized
record rows — people, offices, committees, memberships, votes, sponsorships,
attendance. Deterministic extraction first; LLM extraction only where no
structured parser exists. See the Parsing service section in
`docs/political_verifier_v_1_plan.md`.
