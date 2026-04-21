# Ingestion services

Parent directory for the source adapters (gov.il, Knesset, election results).
Each adapter owns: fetcher, archival step, parser, normalizer, KG upsert, and
provenance link handling. Implementation begins in Phase 2. See the Ingestion
service section in `docs/political_verifier_v_1_plan.md`.
