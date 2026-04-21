# Parsing service

Transforms raw archived artifacts (HTML, PDF, JSON, CSV, text) into normalized
record rows — people, offices, committees, memberships, votes, sponsorships,
attendance. Deterministic extraction first; LLM extraction only where no
structured parser exists. Implementation begins in Phase 2. See the Parsing
service section in `docs/political_verifier_v_1_plan.md`.
