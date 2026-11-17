# Landing Analysis: PLAN-LB-157 — The branch-cleanup pre-merge gate refuses while an earlier manifest step has no terminal record

epic: live-blockers
workstream: WS-01
pr: #2004 (https://github.com/cuioss/plan-marshall/pull/2004)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-157.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-157-pre-merge-refuses-unrecorded-earlier-steps`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `aa525a0344474446dd6a48d763143ee99d105ad6` through the merge queue. Message
`rb-lb-157-pre-merge-refuses-unrecorded-earlier-steps-001.md` carries `total_tokens=unknown` (out of scope under the standing ruling) and
`self-review:budget-exhausted` (see Follow-Ups).

## Deliverable Fidelity vs Spec

Corroborated against `origin/main` at the merge commit: the diff stat (9 files, 1187 insertions), a read of `pre_merge_gate.py` (the sweep, its helpers,
the refusal payload and the `merge()` wiring) and the `branch-cleanup.md` diff.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 enumerate `phase_6.steps` ordered below `branch-cleanup`, check each with `assert-step-recorded --require-terminal`, refuse with a named reason listing the steps, route back to the dispatcher | shipped-as-specified | `_step_sequence_refusal` (re-read): reads the manifest through its own reader, takes the prefix before the `branch-cleanup` entry (`_earlier_manifest_steps`, identity through `canonicalize_step_key`), asks `assert-step-recorded --require-terminal` per step, answers `merge_earlier_step_unrecorded` with `steps[]`, `reason`, `detail`, `remedy`, `dispatched: false`. Wired into `merge()` right after the mutex proof and before the store query (`pre_merge_gate.py:2282-2295`) |
| D1 a not-applicable step, or `done`/`skipped`/`loop_back`, does not block | shipped-as-specified | applicability is the manifest's own answer (a step excluded by `default_on: false` is absent from `phase_6.steps`); `_step_admission` admits `_ADMITTING_STEP_OUTCOMES` and refuses a terminal `failed` and an unconfirmed payload |
| D2 a distinct reason in the merge-gate vocabulary, documented in `branch-cleanup.md` and the dispatcher, with tests (a) to (d) | shipped-as-specified (docs re-read; tests lane-reported) | `MERGE_EARLIER_STEP_UNRECORDED` is a new constant; `branch-cleanup.md` § "Pre-merge step-sequence gate" and the `remedy`-branching disposition are in the diff (re-read); `phase-6-finalize/SKILL.md` is in the stat; `test_pre_merge_step_sequence_gate.py` (716 lines) carries the named tests and was not read here |

Spec HYPOTHESIS (no aggregate sweep exists at the pre-merge gate) confirmed by the lane and consistent with `merge()` before the change (its invariants
were the invocation, mutex, store, head binding and participation).

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — the change is one gate function and its helpers, read in full on the merged tree. By reading: no
build, no test run.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | HYPOTHESIS: no sweep exists at the pre-merge gate | checked | confirms | the lane read the base `merge()` and `branch-cleanup.md:833-870`; the new code adds exactly the missing call |
| L1-2 | OBSERVED: `adr-propose` is order 62 with `default_on: false` | checked | confirms | `workflow/adr-propose.md:6-9` per the lane; the gate's handling follows from absence in the manifest, not from the flag |

**Layer 1 verdict:** no refuting finding.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file | Verdict |
|-------------|------------|--------------------|------------------|---------|
| D1 | `pre_merge_gate.py:762-1081` and `:2282-2295` | `test-first` run named by the lane: 16 failed at the base commit (`TypeError` on the new `step_sequence_check` keyword, `AttributeError` on the new constant) | `_cmd_assert_step_recorded.py` (+20): exports `ASSERTION_STEP_GAP_CODES` so the gate derives its gap vocabulary from the verb's own module (re-read at the consumer, `_assertion_step_gap_codes`) | checked |
| D2 | `branch-cleanup.md` diff, `SKILL.md` | the disposition is prose; its tests are in the new test file | the four existing test files take one keyword each (+11 lines) so their `merge()` calls stub the new seam | docs checked, tests lane-reported |

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `pre_merge_gate.py:2282-2295`; spec Standing Constraints | the sweep runs AFTER the mutex proof, so it runs inside the hold window; the spec's wording was "before the merge-mutex hold window opens or is released and re-acquired" | the cross-plan merge mutex is held while up to one manifest read plus one assertion per earlier step run. Each is bounded at 60 s; the lane states a full 13-step roster's worst case as 780 s. In the normal case these are local reads of milliseconds. A wedged executor would pin the mutex for that long. The doc states the choice ("acquires nothing and releases nothing ... inside the hold window the step already owns") and both refusal halves release the mutex | minor, a documented departure from the spec's wording |
| L3-2 | `branch-cleanup.md` § "Pre-merge step-sequence gate" | a step whose latest record is `loop_back` and was never re-fired | the sweep admits `loop_back`, as the spec said. The doc records the trade ("the dispatcher RE-FIRES a `loop_back` ... a plan may still merge while a step ordered below `branch-cleanup` awaits its re-fire") and names the alternative's deadlock | minor, documented residual |
| L3-3 | `pre_merge_gate.py:1062-1081` | a payload mixing step gaps and read faults | `remedy` is `dispatcher` if ANY row is a gap; the read-fault rows are logged but not the remedy. The re-entry re-asks, the fault then surfaces alone with `remedy: stop`, so the loop terminates | info |
| L3-4 | `pre_merge_gate.py:1031-1050` | a non-string or blank manifest entry | refused as `manifest_steps_unreadable` instead of laundered through `str()`; an unreadable canonicalizer is a fault, not a literal-match fallback | info, correct |
| L3-5 | the last commit `97a2f5063` | message text only | the self-review's last nit was fixed after the round limit and no round re-verified it. The stop-path message is read here and says what it should (`pre_merge_gate.py:956-960`) | info |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (CI `verify / verify` whole-tree green on the final head per the
lane), the test-first run, and the sweep against a live manifest on a plan with a skipped earlier step. No run was made here.

**Layer 3 verdict:** no blocker, no major. L3-1 and L3-2 are documented decisions, not hidden ones.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only | conforms | the new section states the present gate |
| `pm-dev-python:python-core` | explicit exception handling | conforms with a note | the new helpers catch `Exception` with a stated reason (`# an unreadable ... is a failed read, never a crash`) at import and read seams; each converts to a refusal, none passes |
| CLAUDE.md Workflow Discipline | no shell file operations | deviates (self-reported) | `grep`/`tail` on build logs outside the worktree; one `test -f ... && echo` probe was refused for shell chaining |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: CodeRabbit refused on quota twice before reviewing `97a2f5063` (waits of 90 minutes honoured), then auto-reviewed each later head; 12 builds,
  all `daemon_longpoll`, two queued 22 to 518 s behind the daemon's per-directory slot; two builds were still running while small edits landed, and the lane
  does not cite them as head evidence.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited, `review_complete_after_handling`) reviewed `41625c57b` with `97a2f5063` and `ea8c0579b` earlier; six body findings,
  all fixed and replied. Sourcery (optional) refused on quota. Not independently re-run here.
- CI/merge: `verify / verify` whole-tree green on the final head per the lane; queue merge.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-154 and -155 on disjoint surfaces; no collision reported. The spec's Write-Boundary was respected (the one inbox message).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-157 --status shipped`
- [x] row `pr` stamped — `2004`
- [x] row `landing` stamped — `landings/PLAN-LB-157.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-157-pre-merge-refuses-unrecorded-earlier-steps` (from the sender)
- [x] `epic.md` narrative: one Decision bullet for the two landings
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- No executor regeneration is owed (a gate gained a check; the executor maps scripts). A harness sync is owed for the edited bundle sources.

## Follow-Ups

- **L3-1 (the mutex is held across the sweep)** — staged as PLAN-LB-159 D2 (one total budget for the sweep, no greater than 180 s, independent of the roster length).
- **L3-2 (`loop_back` admitted)** — recorded here, no plan; it is the spec's own admitting set and the doc names the trade. Trigger: a plan that merged with an
  earlier step still `loop_back` and never re-fired.
- **Self-review `budget-exhausted`** — message-text nit only; no plan.
- **Archived message `lessons-routing-090.md`** (the origin of this plan) stays as written.
