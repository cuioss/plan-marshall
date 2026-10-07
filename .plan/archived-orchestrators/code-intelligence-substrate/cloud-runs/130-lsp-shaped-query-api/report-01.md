# Run report — 130-lsp-shaped-query-api (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/lsp-shaped-query-api-6p2esn (harness-assigned, kept as-is)    **PR:** [#1207](https://github.com/cuioss/plan-marshall/pull/1207)    **Outcome:** completed (auto-merge armed; landing delegated to the merge queue — this session cannot self-wake to confirm, per § Cloud session affordances)

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
- **CI (PR #1207):** `verify / conclusion`, `verify / verify`, `verify / gate`, `review / review`,
  `dependency-review`, `generate-check` all concluded **success**; `mergeable_state: clean` on the
  first pushed head. (`Sourcery review` and `auto-merge` checks report `skipped`.)
- **PR review — cuioss-review-bot (`cuioss-review-bot`):** ONE actionable finding — *Unhandled
  Exception in `cmd_capabilities`*: `get_module_graph` / `resolve_path_attribution` /
  `load_module_derived` ran outside the `try/except` wrapping `iter_modules`, so an unexpected
  downstream exception would crash rather than return a structured error. **FIXED** — wrapped the
  whole evaluation in one error boundary + added a raising-downstream test (commit 8469daf). No
  thread reply posted: fixing the finding is the visible disposition, and a reply to a bot summary
  would be noise.
- **PR review — coderabbitai:** posted only a rate-limit notice ("Review limit reached; next review
  in 101 minutes") — no review of this diff. Verdict `rate-limited`.
- **PR review — sourcery-ai:** posted only a rate-limit notice ("weekly rate limit of 500000 diff
  characters") — no review of this diff. Verdict `rate-limited`.
- Inline review-thread surface (`get_review_comments`): empty (0 threads).

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(cross-named by `.github/workflows/pr-agent.yml`): `coderabbitai`, `sourcery-ai`, `cuioss-review-bot`.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a "PR Reviewer Guide" review-summary body carrying one actionable finding (the `cmd_capabilities` unhandled-exception). |
| `coderabbitai` | `rate-limited` | Published only a "Review limit reached — next review available in 101 minutes" notice in place of a review. |
| `sourcery-ai` | `rate-limited` | Published only a "reached your weekly rate limit of 500000 diff characters" review body in place of a review. |

**Coverage: 1 of 3 reviewed.** The § Step 8 shortfall disclosure fired (see Contract check) — the
two rate-limited reviewers are routine external quota exhaustion, disclosed and not blocked.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not
  expose a per-session token counter to the running agent). The two verification sub-agents self-
  reported `subagent_tokens` of ~84.4k (cold read) and ~145.4k (deliverable review); the main-loop
  total is not surfaced.
- **Wall-clock:** ~single interactive session on 2026-08-13; the two full `./pw verify` runs took
  ~336s each (reported by the build), plus one initial toolchain bootstrap.
- **Population:** this single Claude Code cloud session's own activity. ⛔ NOT comparable to a
  plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's per-task billing boundary, which a single interactive cloud session does not share.
  The figures above cannot be reconciled to a `metrics.toon` total and are not presented as such.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | DONE — named in § Skills loaded (read via bundle path; plugin not needed). |
| 2 Branch | DONE — harness-assigned `claude/lsp-shaped-query-api-6p2esn`, present on `origin`, kept as-is. |
| 3 Plan directory | DONE — `130-lsp-shaped-query-api/plan.md` exists (prefix preserved) and opens with the first-instruction block. |
| 4 Implement | DONE — six commits, all carrying the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | DONE — every `*.py`-touching commit preceded by a clean `./pw quality-gate` (ruff/mypy/SPDX) + scoped tests. |
| 4 Pushed | DONE — every commit pushed; no unpushed commit remains. |
| 5 Build gate | DONE — Python changed → full `./pw verify` = SUCCESS (19480 passed). |
| 6 Verification sub-agent | DONE — deliverable review (essentially clean; 3 minor doc findings fixed) + plan-mandated cold read (no verb read as renamed). Dispositions in § Findings. |
| 7 PR cycle | DONE — PR #1207; every comment dispositioned (1 finding fixed; 2 reviewers rate-limited). |
| 8 Merge gate | DONE — conditions 1–3 met, shortfall disclosed, auto-merge armed (SQUASH). Landing delegated to the merge queue: this cloud session's self-wake tools (`subscribe_pr_activity`) are approval-gated, so it cannot block-to-confirm `MERGED`; recorded as completed-with-landing-delegated, not partial. |
| 8 Bridge | DONE — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | DONE — this section. |
| 9 What have we learned | DONE — see below. |

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned**. No
`/sync-plugin-cache` owed (machine-local step; a cloud run never performs or records it).

## What have we learned (Step 9)

**No contract change proposed.** This run exercised the lane end to end and every step's artifact was
producible as written. The one point of friction — the cloud session's `subscribe_pr_activity` being
approval-gated so the run cannot self-confirm the merge — is already the exact case the contract
covers under § Cloud session affordances and § Step 8 ("arm-and-hand-off is a completed run"). The
contract's guidance matched the observed environment; the run followed it without ambiguity. Nothing
in this execution produced evidence of a gap, an unproducible artifact, or a command that failed as
written, so there is no evidence-backed amendment to propose.

## Residue

- **Landing confirmation.** Auto-merge is armed on PR #1207 with the merge queue holding until the
  final head's `verify` greens. This session cannot self-wake to read back `state: MERGED`; the
  orchestrator's collect step reads the landing from the PR merge event. If a human is watching, the
  PR page shows the queue state directly.
- **D2-in-a-real-leaf.** The plan asks D2 be verified inside a dispatched leaf with revoked Grep/Glob;
  a true such leaf cannot be synthesised in this session. The two-project-dir envelope-scoping test is
  the recorded proxy, justified in § Findings (the substrate's answer is a function of `project_dir` +
  producers, not of harness tool grants).
