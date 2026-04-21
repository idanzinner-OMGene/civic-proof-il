---
name: cursor-plan-agent
description: >
  Generates a Cursor `.mdc` rule file and companion SKILL.md for a plan-aligned
  sub-agent. Use this skill whenever a user wants Cursor to follow a project plan,
  map tasks to plan items, stay in scope, and checkpoint after every action.
  Trigger on: "cursor sub-agent", "plan-driven agent", "cursor rules for a plan",
  "agent that follows my plan", "cursor stays in scope", or any request to make
  Cursor behave as a disciplined, plan-following assistant.
---

# Cursor Plan-Agent Skill

Produces two files:
1. `plan-agent.mdc` — the Cursor rule file (drop into `.cursor/rules/`)
2. `SKILL.md` — this file, describing how to generate and customize the rule

## When to use
- User has an existing project plan (`plan.md`, `PLAN.md`, Notion export, etc.)
- User wants Cursor to only act within that plan's scope
- User wants per-task checkpoints and deviation reporting

## Inputs to collect before generating
| Input | Required | Default |
|-------|----------|---------|
| Plan file path | Yes | `docs/plan.md` |
| File globs to watch | No | `**/*.py`, `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.jsx`, `**/*.md` |
| alwaysApply | No | `true` |
| Stop-condition list | No | schema changes, new deps, phase unlock, destructive writes |

Ask for the plan file path if not provided. All other inputs use defaults unless the user specifies.

## Generation steps
1. Read this SKILL.md.
2. Collect inputs above (ask only for missing required fields).
3. Write `plan-agent.mdc` to `.cursor/rules/plan-agent.mdc` using the canonical template in `references/mdc-template.md`.
4. Confirm to the user: `✅ plan-agent.mdc written to .cursor/rules/`

## Customization guide
| What to change | Where |
|----------------|-------|
| Plan file location | `Startup` step 1 in the `.mdc` |
| Add/remove watched globs | `globs:` in the YAML frontmatter |
| Add stop conditions | `Stop conditions` section in the `.mdc` |
| Change checkpoint format | `Per-task loop → After completing` block |

## Output contract
The generated `.mdc` MUST contain:
- YAML frontmatter with `description`, `globs`, `alwaysApply`
- A `Startup` block that loads the plan before any action
- A `Per-task loop` with before / during / after phases
- A `Hard rules` block using MUST / NEVER signal words
- A `Stop conditions` list with at least 4 entries

If any of these are missing, regenerate before delivering.

## References
- `references/mdc-template.md` — canonical `.mdc` template with all required sections
- `references/cursor-rules-guide.md` — Cursor rule syntax and `alwaysApply` behavior
