# tests/unit/

Per-package unit tests live alongside each workspace member, not in this root directory.

For example:
- `services/claim_decomposition/tests/` — claim decomposition unit tests
- `services/entity_resolution/tests/` — entity resolution unit tests
- `apps/api/tests/` — API unit tests
- `packages/ontology/tests/` — ontology model tests

This convention avoids pytest rootdir import collisions (adding `__init__.py`
here would cause `ImportPathMismatchError`). Cross-cutting integration tests
live in `tests/integration/`; smoke/alignment tests in `tests/smoke/`.
