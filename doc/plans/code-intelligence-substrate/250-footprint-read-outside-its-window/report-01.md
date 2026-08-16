# Run report — 250-footprint-read-outside-its-window (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/code-intelligence-footprint-window-8vro66` (harness-assigned, kept as-is)    **PR:** _see § PR_    **Outcome:** completed

## Skills loaded

Loaded by reading the bundle source path — the `plan-marshall` plugin is not installed in this cloud
session, so `Skill: {bundle}:{skill}` notation was not used. No skill was unobtainable by both routes.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | always |
| `pm-plugin-development:plugin-script-architecture` | always |
| `plan-marshall:persona-implementer` | production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

`.claude/skills/cloud-plan-lane/SKILL.md` was loaded first, before any other action, as the plan's
first-instruction block requires. That block was present in the plan as handed over and survived the
Step 3 move; no repair was needed.

## Deliverables

### D1 — derive the population of footprint reads (GATE, mutates nothing) — **done**

Published at [`footprint-read-population.md`](./footprint-read-population.md).

Derived from source by sweeping the three derivation primitives (`compute_plan_branch_diff`, reads of
`references.realized_footprint` / `references.modified_files`, and
`_footprint_resolver.resolve_footprint`), **not** from the three surfaces the plan names.

- **13** files carry a footprint derivation; **5** are providers that grade nothing.
- **11** grading/deciding read sites — the D1 population — across **seven** skills
  (`plan-retrospective`, `phase-5-execute`, `manage-execution-manifest`, `script-shared`,
  `manage-config`, `build-pyproject`, `manage-tasks`), all within the single `plan-marshall` bundle.
- **4** of the 11 carried the collapse; **2** were already fixed by sibling plans before this run.

The plan predicted "two named sites became at least four by observation": confirmed and extended — the
population is 11, and the plan's `manage-config` hypothesis is site #9. The hypothesised "shared
footprint-derivation helper" **exists** (`_footprint_resolver.py`) and already carried the third state.

**Split guard.** The plan requires a SPLIT if D1 finds the population materially larger than the named
sites. It is larger (11 vs 3) — but **9 of the 11 were already correct**, so the remaining work was two
sites, well inside this plan's scope. Splitting would have produced a plan with two small fixes and no
gate. Proceeding unsplit is recorded as a deliberate, evidence-backed decision rather than a silent one.

### D2 — a third state at the read seam — **done**

Two sites still collapsed when this run began. Both now return an explicit unresolvable sentinel and
report it with a reason token.

| Site | Was | Now |
|---|---|---|
| `plan-retrospective/scripts/analyze-logs.py` → `resolve_footprint` + ARTIFACT-coverage floor | returned `[]` when no tier answered; consumer `if footprint and artifact_entries == 0` took the falsy branch, so the check **silently did not run** | returns `list[str] \| None`; floor emits `ARTIFACT_COVERAGE_UNMEASURABLE` at `severity: warning` |
| `phase-5-execute/scripts/verify_failure_scope.py` → `_resolve_declared_footprint` + `classify_failure_scope` | returned `set()` on git failure; every error path classified out-of-scope and `exclusively_out_of_scope` set | returns `set[str] \| None`; result carries `footprint_resolved: false`, paths under `unclassified_paths`, flag forced `false` |

The `verify_failure_scope` collapse was the more consequential: `exclusively_out_of_scope` drives
phase-5-execute Step 11 to offer **"Stash foreign files and re-verify"** as the *default* remedy, so an
unmeasurable footprint recommended a real action on no evidence.

The plan's success criterion is adopted verbatim in both sites' docstrings and in the population
document: *an unmeasurable quantity must not be reported as a measured zero.*

**Both directions asserted**, as the plan's Verification section requires:

- `test_unresolvable_footprint_reports_unmeasurable_not_silence` / `test_resolved_empty_footprint_stays_a_measured_zero`
- `test_unmeasurable_footprint_does_not_attribute_failures_as_foreign` / `test_measured_empty_footprint_still_classifies_as_foreign`
- `test_unresolvable_when_no_tier_answers` / `test_present_but_empty_key_is_a_resolved_empty_footprint`

### D3 — fix the recall denominator — **done**

The plan's "second, independently fatal cause", **confirmed first-party before the fix**: a crafted
fixture of two realized modification-intent files alongside three read-intent declarations scored
**"Recall 40% below 70% threshold"** on a perfectly-executed plan — unpassable by construction.

`Affected files:` bullets carry a declared intent, and the extractor discarded it, so `read`-intent
declarations entered the denominator. `extract_modification_intent_files()` is now the denominator.

**How the marker is read is itself load-bearing**, and two verification rounds were spent on it. The
matching regex is byte-identical in shape to the pre-branch version (it differs only by adding a named
capture group, which cannot change what matches); the marker is split off **after** matching, by
`_split_intent_suffix`. This is not incidental: the extractor decides whether a bullet parses AT ALL,
and a bullet that stops parsing is reported as `fail` at `severity: error`. Two intermediate designs
each converted previously-parsing bullets into hard errors — see § Findings F3 and N1. A marker is
recognised only when its token is in the closed `VALID_STEP_INTENTS` vocabulary, imported from
`tools-file-ops` constants rather than restated, and the split always leaves a non-empty path.

An **unannotated** bullet states no intent and is still counted, so the filter cannot manufacture the
opposite error (a vacuously high recall).

**Consumer set derived, not assumed** — the plan's ⚠ on this deliverable. Three consumers share the
denominator:

1. `check_affected_files_recall` — the recall verdict.
2. `check_affected_files_exact_match` — would have reported every read-intent path as `outline_only`
   drift ("Set mismatch").
3. The **LLM-driven** `request_result_alignment` aspect (`references/request-result-alignment.md`) —
   its `partial` rule grades "coverage < 70% of declared Affected files". Corrected alongside. Its
   *scope-creep* rule deliberately keeps the **full** declared list: a file the plan said it would
   touch at all is not a surprise, whatever intent it named.

A **fourth** declaration surface was found and is **deferred, not fixed** — see § Findings R2-D1.

The declaration-**parseability** check still reads the unfiltered bullets, so a deliverable declaring
only read-intent files is not mis-reported as a parse failure; that case became a `skip` carrying its
own distinct reason rather than a 0% recall. `details.read_intent_excluded` publishes the filtered
count on **every** branch, and `declared` means the same thing on every branch, so
`declared + read_intent_excluded` reconstructs the unfiltered total everywhere.

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
`test_unresolvable_and_resolvable_empty_footprints_diverge`.

The asymmetry the plan asks to be stated explicitly is stated in the population document: **readers
fail open to an explicit unknown; composers fail closed and keep the gate.** Keeping a step is
recoverable, dropping one is not — which is the inverse of the reader-side remedy, and is why the two
sides cannot share one fix.

Two stale documentation claims **inside this verified surface** were corrected as part of the
verification (`decision-rules.md` lines 18 and 21) — see § Findings.

### D5 — blast radius on the archived corpus — **BLOCKED on corpus availability**

The archived-plan corpus is a machine-local, git-ignored path not present in this clone. Per the
plan's ⛔ it was **not searched for**; a single non-recursive existence check confirmed
`.plan/archived-plans` is absent, which substantiates the blocked status rather than asserting it
blindly.

Reported as **blocked**, not estimated. No corpus rewrite was in scope either way.

The two counts the plan requires be kept separate are reported separately, for the population that
*was* reachable (the source tree, not the corpus): **11 sites examined, 4 affected.** No coverage
claim is made about archived plans.

Two facts found during verification **bound** what a future D5 could conclude, and are recorded so a
later run does not over-read this one: `plan-retrospective` is `default_on: false` / `presets: [full]`
/ `lane.class: prunable`, so only plans that actually ran the retrospective are affected at all; and
the graded corpus is not confined to validator-checked outlines (this tree's own archived fixture
carries no intent markers), so marker-presence cannot be assumed.

### D6 — tests, each verified to FAIL pre-fix — **done, with one disclosed exception**

| Test | Verified red pre-fix? |
|---|---|
| (a) coverage run with the source absent yields the unknown state | **Yes** — `test_unresolvable_footprint_reports_unmeasurable_not_silence` |
| (b) composition run before any file is written emits no footprint-empty omission | **No — and it could not be.** The composer fix landed in a sibling plan *before* this branch, so the pre-fix state is not reachable here. The coverage exists, passes, and includes the adversarial direction; this run verified its existence rather than re-verifying red-before-green. Recorded as an exception, not narrated as done. |
| (c) a read-intent declaration does not depress recall | **Yes** — see below. |

For (a) and (c), red-before-green was performed by stashing **only the source file**, leaving the tests
in place, running them, then restoring — so the red was observed against real pre-fix code, not
asserted.

**(c), re-derived at the moment of this claim.** `test_recall_read_intent_denominator.py` now holds
**21** tests. Not all 21 are red-pre-fix tests, and the distinction matters:

- At the time of the D3 red-check the module held 9 tests, of which **8 failed** against stashed
  pre-fix source; the headline case failed with the exact defect message *"Recall 40% below 70%
  threshold"*. The 1 that passed pins pre-existing behaviour (the no-declaration skip branch) and is
  correctly green on both sides.
- The other 12 were added by verification rounds 1 and 2. **These are deliberately not red-pre-fix
  tests**: 7 pin *parse-preservation* — properties that held on `origin/main`, were broken by this
  branch's own intermediate designs, and must hold again — so they are green against pre-branch source
  by construction. The remaining 5 pin the `read_intent_excluded` publication contract and the
  reconstruction identity, which did not exist pre-fix.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **8 Python files** (3 sources, 5 test modules) of
18 changed files, so the gate applies:

```
marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py
marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py
marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py
test/plan-marshall/phase-5-execute/test_verify_failure_scope.py
test/plan-marshall/plan-retrospective/test_analyze_logs.py
test/plan-marshall/plan-retrospective/test_analyze_logs_behavior.py
test/plan-marshall/plan-retrospective/test_check_artifact_consistency.py
test/plan-marshall/plan-retrospective/test_recall_read_intent_denominator.py
```

`./pw verify` re-run after the final fix round → **SUCCESS**: `20298 passed, 14 skipped in 318.39s`.
All three sub-steps ran: quality-gate (`ruff … All checks passed!`, `mypy … Success: no issues found in
408 source files`, `SPDX-header check passed`, plugin-doctor `issues[0]`), test-compile (`mypy …
Success: no issues found in 760 source files`), and module-tests.

Per-commit gate: every commit touching `*.py` was preceded by a clean `./pw quality-gate`. No `uv.lock`
churn appeared (`git status --porcelain` empty after each build); all staging was by explicit path,
never `git add -A`.

## Findings

Recorded **per instance**. Two independent verification rounds ran; each found real defects, so each
was followed by fixes and a re-dispatch.

### Round 1 — pre-PR verification sub-agent

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | sub-agent | `artifact-consistency.md` § "Borrowed grammar" still said the annotation is "metadata to discard" — the section that exists to prevent parser/owner drift, describing the retired parser | **Fixed** |
| F2 | sub-agent | `affected_files_exact_match`'s canonical definition still said "the declared set"; only the module docstring had been updated | **Fixed** |
| F3 | sub-agent | **Regression introduced by this branch.** Excluding `(` from the bare path class silently converted `- src/a.py (New file)`, `- src/mod(1).py`, and `- src/a.py (read) - trailing prose` from parsing into non-matches → `fail` at severity error. A *new* false error in the loud-fail branch, reaching the hand-edited and archived outlines archived-mode retrospectives grade | **Fixed** — matching shape restored to pre-branch; marker split off after matching; 5 regression tests added (the property had no coverage in either direction) |
| F4 | sub-agent | `read_intent_excluded` published on 2 of 5 return branches while docs and docstring said it is always published | **Fixed** |
| F5 | sub-agent | `test_annotated_canonical_bullets_extract_with_intent_stripped` name and docstring named the retired behaviour; passed regardless because its fixture pins a modification intent | **Fixed** |
| F6 | sub-agent | `analyze-logs` re-implemented tier 4 with a duplicated `SHIM(B)` block instead of reusing `_footprint_resolver.read_legacy_footprint` | **Fixed** |
| F7 | sub-agent | The plan's ⛔⛔ partial-fix trap requires both causes addressed *and said so*; cause 1 (ordering) was discharged but never stated | **Fixed** — see the population doc's "two independent causes" section |
| F8 | sub-agent | `decision-rules.md:21` said `live_footprint` is "empty before the worktree is materialized"; it is `None`, as the same file says correctly 200 lines later | **Fixed** |

### Round 2 — re-dispatch over round 1's fixes

| # | Source | Finding | Disposition |
|---|---|---|---|
| N1 | sub-agent | **Same class as F3, surviving.** Round 1's marker pattern used an optional head, so a bullet that is entirely a parenthetical (`- (none)`, `- (read)`) reduced to an empty path and was dropped by the caller's `if path:` guard — the same hard `fail`, reached by a different route. Falsified the docstring round 1 had just written | **Fixed** — head is now `.+?`; verified differentially against `origin/main` (28 forms, zero match divergences) |
| N2 | sub-agent | Round 1 made `declared` mean the unfiltered count on one branch and the filtered count on five, breaking `declared + read_intent_excluded == total` on exactly that branch | **Fixed** — one meaning everywhere; the unparseable branch publishes `declared_unfiltered` |
| N3 | sub-agent | Round 1's new grammar bullet claimed a marker is read only at the END of a bullet. True for the bare form, **false** for the backticked form, which anchors at the start of the tail — so the same declaration can land in opposite denominators depending on backticks | **Fixed** — both rules stated per form, asymmetry and its cause named |
| N4 | sub-agent | That bullet contradicted the mirror obligation beside it: the owner's grammar **does** exclude `(`, so an author obeying "mirror the owner" literally would re-introduce F3 | **Fixed** — divergence recorded as deliberate (a validator may reject; a borrowed reader may not) |
| N5 | sub-agent | Any `[a-z-]+` parenthetical truncated a bare path (`reports/summary(final)` → `reports/summary`), silently changing which declared path is compared. Latent — zero occurrences in the tree's 197 real bullets | **Fixed** — markers restricted to the closed `VALID_STEP_INTENTS`, imported not restated |
| N6 | sub-agent | The F8 fix was half-applied: `decision-rules.md:18` still described the same input as empty, leaving the table internally contradictory — worse for a reader than being uniformly wrong | **Fixed** |
| N7 | sub-agent | `read_intent_excluded` had no assertion on the unreadable-references branch (where round 1 added it); one test discarded the status it claimed to check; the reconstruction identity had no test | **Fixed** — 3 tests added |
| N8 | sub-agent | `analyze-logs` residue: stale tier-4 docstring, a bare `None` where the comment claims the sentinel is read by name, and an undocumented sort/dedup behaviour change in tier 4 | **Fixed** |
| N9 | sub-agent | Commit `385f081`'s message says "2 of 5 return branches"; there are 7 returns / 6 details dicts | **Accepted, not corrected** — the commit is pushed and its message is immutable without a force-push that would discard a published history for a cosmetic count. Recorded here instead |
| N10 | sub-agent | The production-shape TOON fixture predated the always-published `read_intent_excluded` key | **Fixed** |

### Round 2 — findings deferred, with reasons

| # | Finding | Disposition |
|---|---|---|
| R2-D1 | **A fourth declaration surface, and it is a phantom.** `phase-3-outline/standards/outline-workflow-detail.md:824`, `phase-3-outline/SKILL.md:399`, and `manage-config/standards/domain-residency-audit.md:51` all state that `affected_files_recall` runs against `**Files expected to mutate:**` and not `**Files to survey:**`. No script reads either field — the extractor splits on `**Affected files:**` only — and `manage-solution-outline`'s Check 3 **rejects** a deliverable using that two-field form, so the contract is unimplementable as written. This is squarely the read-vs-modify semantic D3 addresses | **Deferred.** Pre-existing, and resolving it means deciding whether to *implement* the two-field form or *delete* the claim — a design decision beyond this plan's declared scope. Named precisely here and in § Residue so a follow-up can pick it up rather than rediscover it |
| R2-D2 | `plan-retrospective` reads the worktree via `resolve_live_worktree` but declares no `reads: [worktree]`, so the band contract's checkable ordering rule would not catch the mis-ordering it describes | **Deferred, deliberately.** Adding the declaration would make the step *violate* that checkable rule (it is ordered after the destroyer) and likely fail the doctor gate. The correct resolution is part of the ordering design, not a metadata patch |
| R2-D3 | `references/artifact-consistency.md`'s TOON fragment block shows no `details:` at all, so the newly-universal `read_intent_excluded` key has no worked example in prose | **Deferred** — low value; the fixture (N10) now carries the shape, and adding a full details example to the fragment block is scope growth |

### Self-corrections to this run's own artifacts

Not sub-agent findings — caught by re-deriving my own claims, recorded because the population document
is a deliverable and a false claim in it is the same defect class as a stale doc:

| Finding | Disposition |
|---|---|
| The population doc gave `_references_core.py` a `script-shared/scripts/build/` path; it lives under `manage-references/scripts/` | **Fixed** (`23eab54`) |
| The population doc said "six bundles' skills"; the 11 sites span **seven skills in one bundle** | **Fixed** |
| The population doc concluded the "fires on every plan" claim "holds unnarrowed". The *ordering* is universal, but the *step* is opt-in (`default_on: false`), so the claim **is** narrowed on that axis | **Fixed** — narrowing recorded, and carried into D5's bounds |
| The population doc inferred from Check 3b that cause 2's population "is not marginal". Check 3b establishes the mechanism is reachable, **not** a frequency | **Fixed** — no count is claimed; the defect rests on construction, not frequency |

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc, never
a list transcribed here. M = 3.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | _pending_ | | |
| `cuioss-review-bot` | _pending_ | | |
| `sourcery-ai` | _pending_ | | |

_Completed at the merge gate, from the stored comment bodies across all three surfaces._

## Cost

- **Tokens:** not available to the agent in this session. The two verification sub-agents reported
  their own usage (≈194k and ≈214k subagent tokens); the main session's usage is not exposed.
- **Wall-clock:** first commit `1b14491` at 10:26:47Z. Source: git committer timestamps on this branch.
- **Population:** this single Claude Code cloud session's usage, plus two dispatched verification
  sub-agents. ⛔ **Not comparable** to a plan-marshall `metrics.toon` total, which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a
  boundary a single interactive cloud session does not share. The figures are not made comparable
  here, and no parity is implied.

## Contract check (Step 9)

_Completed before the merge gate._

## What have we learned (Step 9)

_Completed before the merge gate._

## Residue

- **R2-D1 — the phantom `Files expected to mutate:` / `Files to survey:` contract.** Three documents
  describe a two-field declaration form that no script reads and that the outline validator rejects.
  It is a second declaration surface for the same read-vs-modify semantic this plan fixed, so it
  belongs to this programme. A follow-up must decide whether to implement the split or delete the
  claim; it should not be resolved by silently editing prose to match whichever side is easier.
- **R2-D2 — `plan-retrospective`'s undeclared `reads: [worktree]`.** The ordering defect this plan
  documents is real but structurally unenforceable, because the step does not declare the dependency
  the enforcement keys on. Resolving it means deciding the step's correct band, not adding metadata.
- **D5 remains unassessed.** The archived corpus is unreachable from any cloud clone. A local run can
  complete D5; the two bounds recorded under D5 above should be applied when it does.
- **D6(b)'s red-before-green** is not re-checkable on this branch and would need a run based before the
  sibling composer plan landed.
