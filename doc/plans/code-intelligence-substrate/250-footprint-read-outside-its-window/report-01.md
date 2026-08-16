# Run report — 250-footprint-read-outside-its-window (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/code-intelligence-footprint-window-8vro66`    **PR:** _pending_    **Outcome:** _pending_

## Skills loaded

Loaded by reading the bundle source path (the `plan-marshall` plugin is not installed in this cloud
session, so `Skill: {bundle}:{skill}` notation was not used).

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | always |
| `pm-plugin-development:plugin-script-architecture` | always |
| `plan-marshall:persona-implementer` | production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

`.claude/skills/cloud-plan-lane/SKILL.md` was loaded first, before any other action, as the plan's
first-instruction block requires. No skill was unobtainable by both routes.

## Deliverables

### D1 — derive the population of footprint reads (GATE, mutates nothing) — **done**

Published at [`footprint-read-population.md`](./footprint-read-population.md), commit `ecb3fa4`.

Derived from source by sweeping the three derivation primitives (`compute_plan_branch_diff`, reads of
`references.realized_footprint` / `references.modified_files`, and
`_footprint_resolver.resolve_footprint`), **not** from the three surfaces the plan names.

- **13** files carry a footprint derivation; **5** are providers that grade nothing.
- **11** grading/deciding read sites — the D1 population — across six skills.
- **4** of the 11 carried the collapse; **2** were already fixed by sibling plans before this run.

The plan predicted "two named sites became at least four by observation": the sweep confirms this and
extends it — the population is 11, and the plan's `manage-config` hypothesis is site #9. The
hypothesised "shared footprint-derivation helper" **exists** (`_footprint_resolver.py`) and already
carried the third state.

**Split guard.** The plan requires a SPLIT if D1 finds the population materially larger than the named
sites. It is larger (11 vs 3) — but **9 of the 11 were already correct**, so the remaining work was
two sites, well inside this plan's scope. Splitting would have produced a plan with two small fixes
and no gate. Proceeding unsplit is recorded here as a deliberate, evidence-backed decision rather than
a silent one.

### D2 — a third state at the read seam — **done**

Two sites still collapsed when this run began. Both now return an explicit unresolvable sentinel and
report it with a reason token. Commit `8750862`.

| Site | Was | Now |
|---|---|---|
| `plan-retrospective/scripts/analyze-logs.py` → `resolve_footprint` + ARTIFACT-coverage floor | returned `[]` when no tier answered; consumer `if footprint and artifact_entries == 0` took the falsy branch, so the check **silently did not run** | returns `list[str] \| None`; floor emits `ARTIFACT_COVERAGE_UNMEASURABLE` at `severity: warning` |
| `phase-5-execute/scripts/verify_failure_scope.py` → `_resolve_declared_footprint` + `classify_failure_scope` | returned `set()` on git failure; every error path classified out-of-scope and `exclusively_out_of_scope` set | returns `set[str] \| None`; result carries `footprint_resolved: false`, paths under `unclassified_paths`, flag forced `false` |

The `verify_failure_scope` collapse was the more consequential of the two: `exclusively_out_of_scope`
drives phase-5-execute Step 11 to offer **"Stash foreign files and re-verify"** as the *default*
remedy, so an unmeasurable footprint recommended a real action on no evidence.

The plan's success criterion is adopted verbatim in both sites' docstrings and in the population
document: *an unmeasurable quantity must not be reported as a measured zero.*

**Both directions asserted**, as the plan's Verification section requires — an absent source yields the
named state AND a genuinely empty footprint still yields the measured verdict:

- `test_unresolvable_footprint_reports_unmeasurable_not_silence` / `test_resolved_empty_footprint_stays_a_measured_zero`
- `test_unmeasurable_footprint_does_not_attribute_failures_as_foreign` / `test_measured_empty_footprint_still_classifies_as_foreign`
- `test_unresolvable_when_no_tier_answers` / `test_present_but_empty_key_is_a_resolved_empty_footprint`

### D3 — fix the recall denominator — **done**

Commit `e17f605`. This is the plan's "second, independently fatal cause", and it was **confirmed
first-party** before the fix: a crafted fixture of two realized modification-intent files alongside
three read-intent declarations scored **"Recall 40% below 70% threshold"** on a perfectly-executed
plan — unpassable by construction.

The `Affected files:` bullet regex discarded the `(intent)` marker, so `read`-intent declarations
entered the denominator. The marker is now captured, and `extract_modification_intent_files()` is the
denominator. An **unannotated** bullet states no intent and is still counted, so the filter cannot
manufacture the opposite error (a vacuously high recall).

**Consumer set derived, not assumed** — the plan's ⚠ on this deliverable. Three consumers share the
denominator:

1. `check_affected_files_recall` — the recall verdict.
2. `check_affected_files_exact_match` — would have reported every read-intent path as `outline_only`
   drift ("Set mismatch").
3. The **LLM-driven** `request_result_alignment` aspect (`references/request-result-alignment.md`) —
   its `partial` rule grades "coverage < 70% of declared Affected files". Corrected alongside. Its
   *scope-creep* rule deliberately keeps the **full** declared list: a file the plan said it would
   touch at all is not a surprise, whatever intent it named.

The declaration-**parseability** check still reads the unfiltered bullets, so a deliverable declaring
only read-intent files is not mis-reported as a parse failure; that case became a `skip` carrying its
own distinct reason rather than a 0% recall. `details.read_intent_excluded` publishes the filtered
count so a reader can tell a small denominator from a filtered one.

### D4 — the composer's decision fails CLOSED — **already satisfied; verified, not re-built**

No code change was needed. Every composition-time predicate already reads the three-valued footprint
and fails closed:

| Predicate | Fail-closed read |
|---|---|
| `_apply_footprint_gated_canonical_prefilter` | `if footprint is None or not footprint: return phase_5_steps, []` — every canonical survives |
| `_apply_security_class_inactive` | `if affected_files_count > 0 or live_footprint_count is None or …` — `None` is no evidence, step kept |
| `extension_base.should_execute_build` / `manage-config build-decision` | three-valued `unknown` / `not_necessary` / `build`; a gate drops only on the positive `not_necessary` |
| `pyproject_build.cmd_resolve_test_scope` | `footprint_resolvable = resolved_footprint is not None`, fails closed |

The **adversarial** direction the plan demands (make the footprint unresolvable, assert the gate is
KEPT) is pinned by `test_unresolvable_footprint_keeps_the_step`,
`test_unresolvable_footprint_is_a_noop_every_canonical_survives`, and
`test_unresolvable_and_resolvable_empty_footprints_diverge`. 38 such tests pass.

The asymmetry the plan asks to be stated explicitly is stated in the population document: **readers
fail open to an explicit unknown; composers fail closed and keep the gate.** Keeping a step is
recoverable, dropping one is not — which is the inverse of the reader-side remedy, and is why the two
sides cannot share one fix.

### D5 — blast radius on the archived corpus — **BLOCKED on corpus availability**

The archived-plan corpus is a machine-local, git-ignored path not present in this clone. Per the
plan's ⛔, it was **not searched for**; a single non-recursive existence check confirmed
`.plan/archived-plans` is absent, which substantiates the blocked status rather than asserting it
blindly.

Reported as **blocked**, not estimated. No corpus rewrite was in scope either way.

The two counts the plan requires be kept separate are reported separately, for the population that
*was* reachable (the source tree, not the corpus): **11 sites examined, 4 affected.** No coverage
claim is made about archived plans.

### D6 — tests, each verified to FAIL pre-fix — **done, with one honest exception**

| Test | Verified red pre-fix? |
|---|---|
| (a) coverage run with the source absent yields the unknown state | **Yes** — `test_unresolvable_footprint_reports_unmeasurable_not_silence` |
| (b) composition run before any file is written emits no footprint-empty omission | **No — and it could not be.** The composer fix landed in a sibling plan *before* this branch, so the pre-fix state is not reachable here. The coverage exists and passes (38 tests); this run verified its existence and adversarial direction rather than re-verifying red-before-green. Recorded as an exception, not narrated as done. |
| (c) a read-intent declaration does not depress recall | **Yes** — the whole new module was run against the stashed pre-fix source: **8 of 9 failed**, and the headline case failed with the exact defect message "Recall 40% below 70% threshold". The 1 that passed is a guard pinning pre-existing behaviour (the no-declaration skip branch), correctly green both sides. |

Red-before-green for (a) and (c) was performed by stashing only the source file, leaving the tests in
place, running them, then restoring — so the red was observed against real pre-fix code, not asserted.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **4 Python files changed**, so the gate applies:

```
marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py
marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py
marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py
test/... (3 test modules)
```

`./pw verify` → **SUCCESS**: `20286 passed, 14 skipped in 343.52s`. All three sub-steps ran
(quality-gate, test-compile/`mypy(test)` over 760 files, module-tests). Quality-gate reported
`ruff … All checks passed!`, `mypy … Success: no issues found in 408 source files`, `SPDX-header check
passed`, and plugin-doctor `issues[0]`.

Per-commit gate: every commit touching `*.py` was preceded by a clean `./pw quality-gate`. No
`uv.lock` churn appeared (`git status --porcelain` empty after the build); all staging was by explicit
path, never `git add -A`.

## Findings

_To be completed from the verification sub-agent and PR review._

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc, not a
list transcribed here. M = 3.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | _pending_ | | |
| `cuioss-review-bot` | _pending_ | | |
| `sourcery-ai` | _pending_ | | |

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** first commit `1b14491` at 10:26:47Z; see the merge event for the end. Source: git
  committer timestamps on this branch.
- **Population:** this single Claude Code cloud session's usage. ⛔ **Not comparable** to a
  plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary — a boundary a single interactive cloud session does
  not share. The figures are not made comparable here, and no parity is implied.

## Contract check (Step 9)

_To be completed before the merge gate._

## What have we learned (Step 9)

_To be completed before the merge gate._

## Residue

_To be completed._
