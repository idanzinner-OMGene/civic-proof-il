---
name: neo4j-upload-checks
description: Upload graph artifacts into Neo4j and run post-upload sanity checks. Use when validating credentials, constraints, deduplication behavior, and label/relationship integrity.
---

# Neo4j Upload Checks

## Use This Skill When

- Uploading hetero graph data to Neo4j
- Verifying upload quality and schema consistency
- Investigating duplicate nodes/relationships after repeated loads

## Environment Requirements

Use either variable set:

- `G_DB_CONNECTION_STRING`, `G_DB_USER`, `G_DB_PASSWORD`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

If credentials are missing, stop and request them rather than guessing values.

## Relevant Code Paths

- Upload logic and constraints: `src/neo4j_upload.py`
- Notebook upload flow: `notebooks/build_hetero_graph.ipynb`

## Upload Safety Checklist

1. Decide whether to clear existing graph (`clear_existing`) before upload.
2. If not clearing, enable duplicate cleanup when needed (`cleanup_duplicates_first`).
3. Ensure uniqueness constraints exist for `User`, `Scenario`, `ScenarioQuestion`.
4. Upload nodes before relationships.
5. Confirm batch processing completes without failed queries.

## Post-Upload Checks

- Validate node counts by label (`User`, `Scenario`, `ScenarioQuestion`).
- Validate relationship counts by type:
  - `ANSWERED`
  - `IN_SCENARIO`
- Run sample path queries to confirm expected directionality:
  - `User -> ScenarioQuestion -> Scenario`

## Failure Handling

- If counts are inflated, run duplicate cleanup path and re-check.
- If relationships are missing, confirm node IDs and edge keys are being set in upload rows.
- If connectivity fails, verify credentials and network access before retrying upload.
