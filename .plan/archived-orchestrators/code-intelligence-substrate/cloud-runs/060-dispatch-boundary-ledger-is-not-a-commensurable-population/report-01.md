# Run report — 060-dispatch-boundary-ledger-is-not-a-commensurable-population (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/dispatch-boundary-ledger-k8yrwg (harness-assigned)    **PR:** [#1173](https://github.com/cuioss/plan-marshall/pull/1173)    **Outcome:** completed (landing delegated to the merge queue via armed auto-merge)

## Skills loaded

Loaded by path from the bundle source (plugin notation not required):

- `cloud-plan-lane` (first action, governs the run)
- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:persona-implementer` (production code work identity)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)

No conditional skill was needed beyond these — the surface is Python production code
(`manage-metrics.py`) plus its pytest suite, with a small `.adoc`/`.md` doc-touch reconciled inline.

## D1 — GATE: the declared population (analysis only, mutates nothing)

**Which set of dispatches is the ledger's denominator meant to be?** The ledger's per-phase
coverage figure compares two counts that come from **two different producers**:

| Figure | Field | Producer | Population |
|---|---|---|---|
| Numerator | `dispatch_boundary_rows_recorded` | the boundary-file writer `cmd_record_dispatch_boundary`, one row per dispatch that **calls** `record-dispatch-boundary` | dispatches that register a boundary |
| Denominator | `subagent_samples` | `enrich`'s post-hoc transcript walk (`claude_runtime.py`), count of Task-agent returns attributed to the phase window | every dispatch enrich sampled in the window |

These are **not one population**. The numerator is the subset of dispatches whose workflow doc issues
`record-dispatch-boundary`; the denominator is every dispatch enrich found. That is the root of all
three symptoms.

### Dispatch classes — derived from the dispatching code, not from a run

Source of truth: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/call-graph.md`
(the authoritative dispatch topology) cross-checked against every `record-dispatch-boundary` call site
in the phase workflow docs. **Not** derived from any run's emitted classes — a run-derived list cannot
contain a class that never registers, which is the defect.

| # | Dispatch class (`Task: execution-context`) | Registers a boundary? | Evidence |
|---|---|---|---|
| 1 | phase-2-refine (main envelope) | **no** | no `record-dispatch-boundary` in phase-2-refine or `planning.md` |
| 2 | phase-3-outline (main envelope, + change-type LLM fallback) | **no** | no `record-dispatch-boundary` in phase-3-outline |
| 3 | phase-4-plan (main envelope) | **yes** (`--phase 4-plan`) | `workflow/planning-outline.md:468` |
| 4 | phase-5-execute (per-task envelope) | **yes** (`--phase 5-execute`) | `workflow/execution.md:216`, `phase-5-execute/SKILL.md` |
| 5 | phase-6-finalize (per-step dispatches: create-pr, post-run-review) | **yes** (`--phase 6-finalize`) | `phase-6-finalize/SKILL.md:1051` |
| 6 | q-gate-validation (shared: fires from 2-refine Step 13.5, 3-outline Step 11, 4-plan Step 9b) | **no** | never issued from the shared workflow doc |
| 7 | verification-feedback (shared: 5-execute build-runner, 6-finalize pr-comment/sonar/plugin-doctor/pr-state) | **no** | never issued from the shared workflow doc |
| 8 | research (ad-hoc, any phase) | **no** | never issued |
| 9 | enrich-module (6-finalize architecture-refresh, ×N parallel) | **no** | never issued |

phase-1-init runs **inline** in the orchestrator (no dispatch) — it is not a dispatch class and has
nothing to register.

**Two separate figures, both derived from source:**

- **Dispatch classes that exist: 9.**
- **Dispatch classes that register a boundary: 3** (phase-4-plan, phase-5-execute, phase-6-finalize).

So **6 of 9 dispatch classes register no boundary.** The plan's HYPOTHESIS that "the two named phases
(refine, q-gate-validation) are the complete set" is confirmed to be a **FLOOR, not the set** — the
real non-registering set is `{phase-2-refine, phase-3-outline, q-gate-validation,
verification-feedback, research, enrich-module}`.

### The fork: is the class omission the mechanism behind the impossible ratio? — **REFUTED**

The impossible ratio is `dispatch_boundary_rows_recorded > subagent_samples` (numerator **exceeds**
denominator — over-coverage). The class omission makes the numerator **smaller** (fewer boundary
rows than dispatches), i.e. it drives `rows < samples` (**under**-coverage), the opposite direction.
So the omission **cannot** produce the over-coverage ratio.

The two populations do **not** differ by "exactly the non-registering classes": they also differ by an
**accumulation axis**. `cmd_record_dispatch_boundary` always **appends** to the per-phase boundary
file, which persists across re-entries/resume, while `subagent_samples` is a single enrich-window walk
(`claude_runtime.py`). On a finalize loop-back or a resumed run the numerator accumulates while the
denominator reflects one window → `rows > samples`. This is the plan's flagged second cause (the
"resumed run" HYPOTHESIS), independent of the omission.

**Consequence (drives D2/D3):** fixing the omission (D3) does **not** close the impossible ratio (D2).
They are separate defects and get separate fixes — exactly as the plan warned. D3 declares the
excluded classes (which explains the `rows < samples` shortfall); D2 makes `rows > samples` a loud
failure (which the omission never explained).

## Deliverables

Per deliverable: what was done, in which commit, and its verification state.

- **D1 — GATE** (commit `02d098a`, analysis-only): complete. Class count 9,
  registering count 3, both source-derived from the call graph. The fork
  (omission → impossible ratio) is **refuted** — the omission drives
  under-coverage, the impossible ratio is over-coverage from a separate
  (accumulate-vs-window) cause. Mutates nothing.
- **D2** (commit `2312559`): a numerator > denominator no longer renders
  `complete`. New `_boundary_coverage_state` classifier (undecidable / partial /
  exact / **over**); the `over` case renders a loud `FAILURE` naming both
  producers and is refused the reconciliation maximum (not just the display).
  Verified by `test_over_coverage_renders_failure_naming_both_populations` and
  `test_over_covering_measure_is_ineligible_for_the_maximum` (both fail-first).
- **D3** (commit `2312559`): `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` constant
  (source-derived, 6 non-registering classes) rendered as a declaration the
  coverage figures reference. Verified by `test_excluded_classes_are_named_in_the_report`,
  the source-derivation guard, and the negative control (a dispatched phase's
  shortfall is declared, not silently shrunk).
- **D4** (commit `2312559`): `_reconciliation_relation_clause` renders the true
  `>` / `=` / `<` relation; exact agreement reads as agreement. Verified by the
  three-way distinction test (equal + smaller fail-first; larger is the labelled
  characterization arm).
- **D5** (commit `2312559`, mypy typing fix `952c4e5`): 8 tests in
  `test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py`.
  Fail-first confirmed: **7 failed, 1 passed** against unmodified code (the 1
  passing is the declared `larger` characterization arm); **8 passed** after the
  fix.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → two Python files changed
(`manage-metrics.py`, the new test), so the gate is `./pw verify`.

- **Fail-first evidence** (unmodified code): `7 failed, 1 passed` — the impossible
  ratio rendered `— complete`, no exclusion declaration existed, and the
  comparator rendered `> total_tokens` for the equal / smaller cases.
- **`./pw quality-gate`**: `status: pass`, `total_issues: 0`, empty `issues[]`.
- **`./pw verify`** (full): **19052 passed, 14 skipped**, `verify: SUCCESS`
  (after the one mypy `no-any-return` fix in the new test helper). No regression
  in the 398-test manage-metrics suite.

## Findings

**Pre-PR verification sub-agent** (independent `general-purpose`, read-only, two passes).
Verdict pass 1: D2–D5 all PASS; out-of-scope respected (no `record-dispatch-boundary`
call added, no display clamping); dispatch topology independently re-derived from the call
graph (9 classes, 3 register, 6 excluded — matches the constant); fail-first evidence
consistent (7 fail / 1 characterization pass pre-fix).

Beyond-diff stale-claim sweep findings — all the same class (narrative that still described
the pre-fix *partial-only* eligibility rule after `over` was made ineligible too):

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | `manage-metrics.py` `_DISPATCHED_MEASURE_FIELDS` preamble comment | "refused the maximum when it is PARTIAL" — omits `over` | **fixed** (commit `b1d85f5`) |
| 2 | `manage-metrics.py` rendered reconciliation annotation clause | "a partial measure is ineligible" — user-facing, omits `over` | **fixed** (commit `b1d85f5`) |
| 3 | `manage-metrics.py` `_read_dispatch_boundary_totals` docstring | "mark the measure PARTIAL and refuse it the maximum" — omits `over` | **fixed** (commit `b1d85f5`) |
| 4 | `manage-metrics.py:1511-1516` reconciliation-loop comment | "a partial boundary measure … ineligible" — omits `over` (residual, found on re-verify) | **fixed** (commit `344cb43`) |
| 5 | `manage-metrics.py:~1768` coverage-bullet preamble comment | mentions only "partial" as the illustrative floor case | **rejected — not a defect**: it is motivation for stating coverage on every render, not an eligibility-rule claim; the render below handles all four states explicitly. Sub-agent concurred. |

Re-verification pass confirmed findings 1–3 correctly account for the `over` state, the fix
introduced no new stale claim, and a final grep-level sweep found only residual #4 (now
fixed) — no other partial-only eligibility narrative remains.

**CI**: `verify / conclusion` **success** on head `3c80d791` (with `verify / verify`,
`verify / gate`, `review / review`, `dependency-review`, `generate-check` all success;
`Sourcery review` and `auto-merge` skipped). `mergeable_state: clean`. No CI findings.

**PR review**: no actionable findings. `cuioss-review-bot` posted a clean "PR Reviewer
Guide" (contains tests · no security concerns · no major issues). `coderabbitai` and
`sourcery-ai` posted only rate-limit notices (no diff review). Inline review threads: 0.
Nothing to fix or reply to.

## Reviewer participation

Expected population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry
doc (`pr-agent.md` → `cuioss-review-bot`, `coderabbit.md` → `coderabbitai`, `sourcery.md` →
`sourcery-ai`), cross-named by `.github/workflows/pr-agent.yml`. Verdicts derived from the
stored comment/review bodies:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted "PR Reviewer Guide 🔍 — PR contains tests · No security concerns identified · No major issues detected": an explicit clean review over the diff. |
| `coderabbitai` | `rate-limited` | Published only "Review limit reached … Next review available in 43 minutes" — engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published a review reading "you have reached your weekly rate limit of 500000 diff characters"; its `Sourcery review` check concluded `skipped`. |

**Coverage: 1 of 3.** Step 8 shortfall disclosure fired: "Review coverage 1 of 3 —
`cuioss-review-bot` reviewed (no findings); `coderabbitai` rate-limited (window reopens ~43
min); `sourcery-ai` rate-limited (weekly quota)." Per the contract this is a disclosure, not
a block — rate limits are routine and outside our control, so the merge proceeds once
conditions 1–3 hold.

## Cost

- **Tokens:** not available to the agent as a precise figure in this session — the harness
  does not surface a per-run token total to the agent. Not stated rather than guessed.
- **Wall-clock:** run start ~21:06 UTC (branch push / D1) to merge-gate ~22:05 UTC — roughly
  one hour, including two independent verification sub-agent passes, three full `./pw verify`
  runs locally (~6–7 min each), and the CI `verify` wait (~14 min). Source: commit and
  PR-event timestamps.
- **Population:** this single Claude Code cloud session's usage. ⛔ **NOT comparable** to a
  plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree
  under plan-marshall's per-task billing boundary — a boundary this interactive cloud session
  does not share. The figures cannot be made comparable, so no parity is implied.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — 6 skills, all by bundle path (§ Skills loaded). |
| 2 Branch | Done — harness-assigned `claude/dispatch-boundary-ledger-k8yrwg`, kept as-is, on `origin`. |
| 3 Plan directory | Done — `060-…/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — commits carry the trailer; D1–D5 addressed. |
| 4 Per-commit gate | Done — every `*.py` commit preceded by a `total_issues: 0` / empty `errors[]` quality-gate log. |
| 4 Pushed | Done — no unpushed commit remains. |
| 5 Build gate | Done — Python changed → `./pw verify` run over the final state: 19052 passed, 14 skipped, SUCCESS. |
| 6 Verification sub-agent | Done — two passes; 4 stale-claim findings fixed, 1 rejected-with-reason. |
| 7 PR cycle | Done — PR #1173; both comment surfaces read; no actionable comment. |
| 8 Merge gate | Conditions 1–3 met; shortfall disclosed (1-of-3); auto-merge armed (SQUASH). Landing delegated to the merge queue (§ Residue). |
| 8 Bridge | No write landed under `doc/plans/` outside this plan's directory. |
| 9 This check | This table. |
| 9 What have we learned | Below. |

GitHub access path: **GitHub MCP server** (cloud path). Branch form: **harness-assigned**
(`claude/*`, kept as-is). No `/sync-plugin-cache` owed (machine-local build step; a cloud run
never performs or owes it).

## What have we learned (Step 9)

One minor, run-evidenced candidate: the § Step 8 condition-1 text enumerates
`mergeStateStatus` values `BLOCKED` and `UNSTABLE` but not **`clean`**, which is the value
this run actually observed once the required `verify` check went green (`mergeable_state:
clean`, no non-required contexts pending). `clean` is the "all required green AND nothing else
pending — fully mergeable" state; a reader following the contract literally finds only
`BLOCKED`/`UNSTABLE` described. Proposed amendment: add `clean` alongside `UNSTABLE` as a
"required contexts satisfied → may arm" state. This is a **doc-completeness** nit, not a gap
that changed the outcome (the contract's intent — read required-ness from GitHub's own
computation — was clear and correctly applied). Presented to the operator for a decision; not
self-approved and not shipped in this PR. The one in-run friction (a `send_later` call failed
on a wrong MCP server prefix) was an agent error, not a contract defect, and turned out
unnecessary — the merge gate was driven entirely by in-session read-polling, exactly as the
contract's "Manual read-polling" path prescribes.

## Residue

- **Landing**: auto-merge is armed (SQUASH) on PR #1173 with required checks green; the merge
  queue lands it. This session delegates the `state: MERGED` confirmation to the
  orchestrator's collect step (per § Step 8 arm-and-hand-off) — or self-confirms on re-entry
  if the session is still active when the queue lands it. The squash merge SHA does not exist
  until then and is read from the PR merge event, not embedded here.
- **Review coverage**: 1-of-3 by reviewer rate limits (disclosed above); both rate-limited
  bots' windows reopen on their own schedules. No action owed — re-requesting is optional and
  the merge does not wait on it.
- **Contract amendment**: the `clean` `mergeStateStatus` doc nit awaits an operator decision;
  if accepted it ships as a separate `chore/` PR touching only the skill.
