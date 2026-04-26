# Convention: Prompt cards

All LLM interaction in civic-proof-il goes through versioned YAML
prompt cards under `packages/prompts/src/civic_prompts/<category>/v<N>.yaml`.
The four allowed categories (plan line 441) are:

* `decomposition` — free-form statement → candidate atomic claims
* `temporal_normalization` — time phrase → structured scope (fallback
  only; canonical path is deterministic, see ADR-0006)
* `summarize_evidence` — evidence list → reviewer-facing paragraph
* `reviewer_explanation` — reviewer note templating

No other LLM categories are allowed. New categories require an ADR.

## Card schema

```yaml
category: decomposition
version: 1
languages: [he, en]
model_hint: <free-form; consumer decides>
system: |
  <system prompt body>
user_template: |
  <user prompt with {placeholders}>
metadata:
  owner: <team/person>
  created_at: <ISO date>
  rationale: <why this card exists>
```

## Loader

```python
from civic_prompts import load_card
card = load_card("decomposition", version=1)
prompt = card.user_template.format(statement="...")
```

`load_card` reads YAML; `available_cards()` lists every file.

## Packaging gotcha

`packages/prompts/pyproject.toml` MUST declare every category under
`[tool.hatch.build.targets.wheel.force-include]`:

```
"src/civic_prompts/decomposition" = "civic_prompts/decomposition"
```

The `shared-data` key looks correct but maps to a different install
location; using it silently breaks `load_card` at runtime.

## Don't

* Don't edit a shipped version in place. Bump to `v2.yaml` and leave
  `v1.yaml` intact so old verdicts remain reproducible.
* Don't rely on prompt cards to enforce output shape; the caller (e.g.
  the claim decomposer) always validates against
  `civic_ontology.claim_slots`.
