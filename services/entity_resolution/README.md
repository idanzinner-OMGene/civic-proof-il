# Entity resolution service

Links names to canonical entities in the order: official external IDs → exact
normalized Hebrew match → curated aliases → transliteration normalization →
fuzzy matching → LLM fallback for ambiguous ties only. Maintains the alias
table and surfaces ambiguity to review. Implementation begins in Phase 3. See
the Entity resolution service section in `docs/political_verifier_v_1_plan.md`.
