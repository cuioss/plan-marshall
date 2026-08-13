# Run report — 130-lsp-shaped-query-api (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/lsp-shaped-query-api-6p2esn (harness-assigned, kept as-is)    **PR:** (pending)    **Outcome:** in-progress

## Skills loaded

- `cloud-plan-lane` (first action, via `Skill:`)
- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)
- `plan-marshall:persona-implementer` (production code identity)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)

GitHub access path: GitHub MCP server (cloud session). Branch form: harness-assigned `claude/*`.

## Split-guard verdict (recorded, per plan line 109-111)

The plan flags five deliverables at the split guard, with the natural cut being *vocabulary
reshape (D1+D2+D3+D5)* versus *the substitute primitive's measurement contract (D4)*.

**Verdict: keep together, execute as one plan/PR.** Rationale grounded in the observed surface:

- D1/D2/D4 all land in the same three Python files (`architecture.py` argparse surface,
  `_cmd_client_handlers.py` handlers, `_cmd_client_query.py` derivation) and the same two doc
  surfaces (`client-api.md`, `SKILL.md` Canonical invocations). Splitting doubles the review
  and doc-churn surface for no isolation benefit.
- D4 is small (one flag + one field on the existing `cmd_search` handler) — not worth its own
  plan/PR.
- D5 documents all four together (the LSP model, the mapping table, and the search contract
  live in the same concepts/user/developer pages), so a split would fracture one doc narrative.

## D1 shape — interpretation recorded (plan says shape is DECIDED, do not re-derive)

The plan's D1 text names two overlapping sets: line 62 maps `impact → references`,
`find`/`which-module → workspace-symbol`, `module`/`derived-module → hover`; line 66 names
`path, impact, find, which-module` as the `workspace/executeCommand` residue that keeps its
names. These are reconciled — not re-derived — as: **the mapping table records each verb's
conceptual LSP method (line 62), while the four traversal/inventory verbs stay reachable under
their own names as the executeCommand residue (line 66).** Both hold at once — a verb is
reachable BOTH via its LSP-named facade AND via its own name — which is exactly the plan's
"the mapping is not one-to-one and the residue is large."

Realization (additive, non-breaking): a new `lsp` subcommand namespace whose subcommands are
thin facades dispatching to the existing handlers, plus a per-verb mapping table. The LSP
methods covered are exactly those the two LSP plans name (this plan line 62 + 240-skill-lsp-server
"the substrate already speaking definition / references / hover"):

| LSP method | `lsp` facade verb | dispatches to | note |
|---|---|---|---|
| `textDocument/hover` | `lsp hover --module M` | `module` | module info |
| `textDocument/references` | `lsp references --module M` | `impact` | reverse-dependency closure |
| `textDocument/definition` | `lsp definition --command C [--module M]` | `resolve` | command → executable |
| `workspace/symbol` | `lsp workspace-symbol --query Q [--category C]` | `find` | path-glob workspace search |
| `workspace/executeCommand` | (residue, own names) | `path`, `impact`, `find`, `which-module`, `graph`, `neighbors` | no standard LSP method |

The four residue verbs remain reachable unchanged — the facade is purely additive.

## Deliverables

- **D1 — LSP-shaped facade + mapping table:** (in progress)
- **D2 — capability-report verb (`capabilities`):** (in progress)
- **D3 — vacuous-consumer guard (refine feasibility):** (in progress)
- **D4 — search measurement contract (`--ignore-case` + `file_count`):** (in progress)
- **D5 — documentation:** (in progress)

## Build gate

(pending)

## Findings

(pending — verification sub-agent, CI, PR review)

## Reviewer participation

(pending)

## Cost

(pending)

## Contract check (Step 9)

(pending)

## What have we learned (Step 9)

(pending)

## Residue

(pending)
