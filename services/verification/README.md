# Verification service

Compares normalized claims to retrieved evidence, assigns a verdict, computes
rubric-based confidence, and decides abstain or escalate. Final truth decision
stays deterministic/rule-governed in v1; LLMs may summarize evidence, never
decide truth. Implementation begins in Phase 4. See the Verification service
section in `docs/political_verifier_v_1_plan.md`.
