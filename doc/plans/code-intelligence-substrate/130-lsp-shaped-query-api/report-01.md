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

- **D1 — LSP-shaped facade + mapping table:** DONE. New `lsp` subcommand group in
  `architecture.py` (`hover`→`module`, `references`→`impact`, `workspace-symbol`→`find`,
  `definition`→`resolve`); handlers `cmd_lsp_*` in `_cmd_client_handlers.py` (pure dispatch,
  answer unchanged). Residue verbs (`path`/`impact`/`find`/`which-module`) untouched. Per-verb
  mapping table in `client-api.md` § "LSP-shaped query facade". Commit 0d12e4b. Tests:
  `test_lsp_facade.py` (facade == underlying verb; residue reachable).
- **D2 — capability-report verb (`capabilities`):** DONE. `cmd_capabilities` reports
  module_edges / path_attribution / content_search, each `not_derivable`/`derivable` (+
  `derived_count`) or `available`/`unavailable`; read from producers that actually ran, per-call
  (uncached), envelope-scoped (`project_dir`). Commit 0d12e4b. Tests: `test_capabilities.py`
  (cannot-derive vs derived-nothing vs derived-N; envelope-scoping).
- **D3 — vacuous-consumer guard (refine feasibility):** DONE. `refine-workflow-detail.md`
  Feasibility Check now gates dependency-direction reasoning on graph `resolver_count`:
  `resolver_count: 0` → `FEASIBILITY: UNDERIVABLE`, never a silent clean pass. Commit 0d12e4b.
  Negative-control test `test_feasibility_underivable_guard.py` asserts the two empty graphs are
  classified oppositely.
- **D4 — search measurement contract (`--ignore-case` + `file_count`):** DONE. `search --content`
  gains `--ignore-case` (composes with `--literal`; metacharacter pattern matched verbatim AND
  case-insensitively); `file_count` (distinct paths) added alongside `count` (rows); regex-mode
  `(?i)` documented. Commit 0d12e4b. Tests added to `test_search_content.py`.
- **D5 — documentation:** DONE. concepts/`code-intelligence.adoc` (LSP query model + capability
  report), developer/`lsp-query-facade.adoc` (new, verb mapping) + README registration,
  user/`code-search.adoc` (--ignore-case, file_count, capabilities, LSP vocab), `SKILL.md` +
  `client-api.md` (contract + Canonical invocations). Commit 6126013.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → non-empty (manage-architecture scripts +
tests). `./pw quality-gate` clean (`issues[0]`, plugin-doctor marketplace-wide). Full `./pw verify`
first failed test-compile on two mypy `no-any-return` in the new test helpers; fixed (`bool(...)`
wrap and a `dict`-annotated local). Re-run full `./pw verify` → **`verify: SUCCESS` — 19480 passed,
14 skipped in 336s**, coverage COMPLETE (mypy production+test, ruff, SPDX, plugin-doctor
marketplace-wide, whole-tree pytest). A final `./pw quality-gate` over the doc-fix commit (0df29ed)
is also clean (`issues[0]`, `broken-relative-link: 0`, `scan_manage_invocation: 0`).

## Findings

- **Verification sub-agent — cold read (D5, plan-mandated):** un-primed agent read the facade docs
  (client-api.md § facade, SKILL.md, lsp-query-facade.adoc, code-intelligence.adoc) and answered
  which verbs it believed were renamed/removed. Verdict: **NONE — all prior verbs remain reachable
  under their own names**, and no document misled it toward a rename reading. This is the correct
  reading the plan's D5 verification requires — the facade documentation PASSED the cold read.
- **Build (test-compile):** 2 mypy `no-any-return` findings in `test_feasibility_underivable_guard.py`
  and `test_capabilities.py` — FIXED (source: local build), commit 8159710.
- **Verification sub-agent — deliverable review:** verdict *essentially clean, no correctness
  defects*. All five deliverables verified as implemented-as-specified with tests. Findings:
  - *Finding 1 (LOW, stale synopsis):* `persona-plan-marshall-agent/…/tool-usage-patterns.md` search
    synopsis omitted `[--ignore-case]` — **FIXED** (commit 0df29ed).
  - *Finding 2 (INFO, partial hint):* `agent-behavior-rules.md` content-lookup hint named `--literal`
    but not `--ignore-case` — **FIXED** (commit 0df29ed).
  - *Doc-fidelity note:* `capabilities` TOON examples elide the per-entry `verbs`/`producers` list
    fields — **FIXED** by an explicit elision note (commit 0df29ed).
  - *Caveat: D2-in-a-real-leaf.* The plan asks D2 be verified inside a dispatched leaf. The
    substrate's answer is a pure function of `project_dir` + the producers that ran, not of the
    leaf's harness tool grants (it is a filesystem-reading Python script), so orchestrator-vs-leaf
    divergence reduces to `project_dir` divergence — which `test_capabilities.py`'s two-project-dir
    envelope-scoping test exercises directly. Recorded as the available proxy; a true
    revoked-Grep/Glob leaf cannot be synthesised in this session.
  - *Caveat: suite not run by the agent* — now closed: the full `./pw verify` ran to SUCCESS (above).
- **CI + PR review:** recorded below as they arrive.

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
