# Landing Analysis: PLAN-LB-159 — A bounded merge-mutex sweep, the first-drift wording, and a bundle-qualified agent name that says why it missed

epic: live-blockers
workstream: WS-01
pr: #2008 (https://github.com/cuioss/plan-marshall/pull/2008)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-159.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-159-follow-ups-sweep-hold-bound-probe-wording-agent-diagnostic`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `caeb85175a1f549ead939d3144241c21dad5e878` through the merge queue (merge-group run 44088157679). Message
`rb-lb-159-follow-ups-sweep-hold-bound-probe-wording-agent-diagnostic-001.md` carries `total_tokens=unknown` (out of scope under the standing ruling) and
`self-review:clear` after three rounds.

## Deliverable Fidelity vs Spec

Corroborated against `origin/main` at the merge commit: the diff stat (11 files, 475 insertions, 27 deletions) and a read of the merged diff of
`pre_merge_gate.py`, `branch-cleanup.md`, `execution-recovery.md`, `runtime_base.py`, `_claude_runtime_impl.py`, `contract.md` and the platform-runtime
`SKILL.md`. The three test files were checked by test name only.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 the unchanged-probe block states the no-recorded-probe case; the two existing bullets keep their text | shipped-as-specified | `execution-recovery.md:19` (one added bullet, no deletion): the first drift return records its signature with the same `manage-status metadata --set` call, continues with step 1, and `drift_unchanged` "cannot fire on this return" |
| D2 one total budget, a named constant no greater than 180 s, independent of the roster; lesser-of per verb; a spent budget refuses `merge_earlier_step_unrecorded` with `remedy: stop` and `step_record_unreadable` rows for the unread steps; verdicts inside the budget unchanged; `branch-cleanup.md` states the bound and its figure | shipped-as-specified | `_STEP_SEQUENCE_TOTAL_BUDGET_SECONDS = 180`; `_step_sequence_refusal` computes one `deadline = clock() + budget` before the manifest read, hands the manifest read `min(60, remaining)` and each assertion `min(60, remaining)`, and on `remaining <= 0` takes `earlier[index:]` as unread. `_sequence_refusal_payload(..., unread_steps=...)` forces `remedy: stop` and names only the unread steps. `branch-cleanup.md` states 180 s in the hold-window paragraph, the reason vocabulary and the `remedy: stop` disposition. The shape chosen is the spec's first (a budget inside the sweep, not the sweep ahead of the hold window) |
| D3 `{bundle}:{name}` refused as `prompt_not_found` naming the stem; guard unchanged for path/glob in either half; bare-stem resolution and every existing miss unchanged; `contract.md` and `SKILL.md` carry it | shipped-as-specified | `_qualified_agent_stem` (`runtime_base.py`) accepts exactly one bundle half, one colon, one name half, both halves passing `_is_agent_file_stem`; `_claude_runtime_impl.py` calls it only inside the `agent_path is None` branch, so no name that resolved before changes. `contract.md` (§ arguments, error table, a worked example) and `SKILL.md` (error row) carry the message |
| D4 tests for D1 and D2 | shipped-as-specified (lane-reported) | `test_pre_merge_step_sequence_gate.py` (+182) has the budget-named-and-bounded test, the over-budget roster, the gap-then-budget case, the fitting roster and the per-verb lesser-of test; `test_baseline_drift_recovery.py` (+27) pins the D1 sentence. Not read in full |
| D5 tests for D3 | shipped-as-specified (lane-reported) | `test_agent_file_versioned_layout.py` (+95); the lane reports the two mutation-proven guard tests failing under a bypassed `_is_agent_file_stem`. Not read in full |

Both spec HYPOTHESES confirmed by the lane and by this read (the `min(per-verb, remaining)` hand-off through `_run_verb`'s `timeout`; the doc-contract suite
already asserts the unchanged-probe block). Verify-first (b), that no caller other than `merge()` reaches `_step_sequence_refusal`, is confirmed by the lane.

**Scope addition beyond the spec's Expected Surface:** `platform-runtime/scripts/claude_runtime.py` (+1 line, the re-export of `_qualified_agent_stem`
beside `_parse_agent_frontmatter`). Same skill as the named `runtime_base.py`; a surface clarification, not a new module.

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — one gate function, one helper and three prose edits, read in full on the merged tree. By reading: no
build, no test run.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | OBSERVED: `_STEP_SEQUENCE_VERB_TIMEOUT_SECONDS = 60` bounds each verb, worst case 780 s for 13 steps | checked | confirms | the pre-merge diff base shows the constant and its comment; the new total budget is what the spec asked for |
| L1-2 | OBSERVED: `_AGENT_STEM_CHARS` has no `:` so a qualified value fails the guard | checked | confirms | `_qualified_agent_stem` relies on exactly that: the halves are tested by the same guard |

**Layer 1 verdict:** no refuting finding.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file | Verdict |
|-------------|------------|--------------------|------------------|---------|
| D1 | `execution-recovery.md:19` | doc-contract test `test_the_unchanged_probe_states_the_first_drift_case`; the lane marks it `none` (doc-only) | none | checked |
| D2 | `pre_merge_gate.py` `_step_sequence_refusal` loop and `_sequence_refusal_payload` | `mutation-after` run: the constant mutated 180 to 10 000 fails the budget and over-budget tests (job log named) | none | checked |
| D3 | `runtime_base.py` `_qualified_agent_stem`, `_claude_runtime_impl.py` miss branch | `mutation-after` runs: the diagnosis reverted fails the stem-naming test; a bypassed guard fails both guard tests (three job logs named) | `claude_runtime.py` re-export | checked |
| D4, D5 | the test files | the runs above | none | lane-reported |

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `pre_merge_gate.py` `_step_sequence_refusal` | the last verb is handed a very small remainder (for example under a second) | the verb is cut off by its own timeout and answers `step_record_unreadable` although the step may be recorded; the refusal is `remedy: stop`, so the plan is not looped back and an operator reads the payload. The bound cannot be exceeded, at the price that a plan whose roster is slow but healthy can be refused at the edge of the budget. Not reachable in the normal case, where each local read takes milliseconds | info, inherent to a hard budget |
| L3-2 | `pre_merge_gate.py` budget refusal | a real step gap read before the budget ran out, then the budget spent | `remedy` is `stop` whatever the rows say, so the gap row is in `steps[]` but the dispatcher is not offered the loop-back. The doc states it ("`stop` is not purely row-derived"), and the re-run after the read is made to fit reaches the gap | info, documented |
| L3-3 | `_qualified_agent_stem` | `foo:bar` where `bar` is not an agent either | the message says "pass 'bar'" without checking that `bar` resolves; the next call then answers the plain miss with the roots. Two steps, both honest; the message names "the stem the value would have meant", as the spec asked | info |
| L3-4 | `execution-recovery.md:19` against the first-drift record | an interruption between recording the first-drift signature and `set-phase 2-refine` | the next return reads the recorded signature as equal and stops with `drift_unchanged`. CodeRabbit raised it; the lane did not change the order, because the record-then-step-1 order is the spec's own wording. It fails safe (an operator-confirmed reconcile) and is bounded by the consecutive-drift cap. The lane named it as a follow-up | minor, fail-safe, pre-existing |
| L3-5 | `branch-cleanup.md` hold-window paragraph | none | the 180 s figure appears in prose at four places (hold window, `remedy` paragraph, vocabulary, disposition) and as the constant; a later change to the constant needs five edits. The lane's own review noted the repetition in the message string | info |
| L3-6 | the merge mutex's liveness-based reclaim (`manage-locks/SKILL.md`) | a hold of up to 180 s | the mutex is reclaimed on holder liveness, not on a fixed lease, so a 180 s hold is not auto-reclaimed while the holder lives. Read in the skill doc only; the hold's interaction with a waiter's admission budget was not traced | not shown by reading |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (the lane reports 34099 tests green at `e2ae38e`; CI run
44077543098 failed once on a teardown timeout in `test_executor_recovery.py` and passed on re-run), the mutation runs, and the sweep under a real wedged executor.
No run was made here.

**Layer 3 verdict:** no blocker, no major. L3-1 to L3-3 and L3-5 are documented or inherent; L3-4 is a pre-existing fail-safe the lane declined with a stated reason.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only, no duplication | conforms with a note | the new prose states the present gate; L3-5 is the repeated figure |
| `pm-dev-python:python-core` | explicit exception handling, typed signatures | conforms | the new helpers add keyword-only typed parameters and no exception handling |
| CLAUDE.md Workflow Discipline | no shell file operations | deviates (self-reported) | about 27 read-class shell operations (17 `grep`, 5 `tail`, 3 `ls -la`, 1 `find`, 1 `readlink`); the guard refused two (R1 shell chaining, R7 a mangled edit path), both corrected |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: 22 builds, all `daemon_longpoll` and routed; two `quality-gate` runs failed on `ruff format --check` because the gate auto-fixed formatting, each re-run
  green. One local `verify` hit an environment flake (`[Errno 39] Directory not empty` in the target-tree generator precondition), re-run green. One CI run failed on a
  300 s `shutil.rmtree` teardown timeout in a module this plan does not touch, and passed on re-run.

## Routing and Merge Behavior

- Review: CodeRabbit (required, `review_complete_after_handling`) reviewed `e2ae38e`, the merge head, with a qualifying review (`sourceCommitId` = `coveredCommitId`); its one
  inline finding (the first-drift record order) was replied to with a stated reason and resolved. Sourcery (optional) refused on quota. Not independently re-run here.
- CI/merge: `verify` green on `e2ae38e` after one re-run of an unrelated teardown timeout; queue merge.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-158 on declared-disjoint surfaces; no collision reported. The Write-Boundary was respected (the one inbox message).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-159 --status shipped`
- [x] row `pr` stamped — `2008`
- [x] row `landing` stamped — `landings/PLAN-LB-159.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-159-follow-ups-sweep-hold-bound-probe-wording-agent-diagnostic` (from the sender)
- [x] `epic.md` narrative: one Decision bullet for the landing
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- No executor regeneration is owed (a gate and a dispatch miss message changed; the executor maps scripts). A harness sync is owed for the edited bundle sources:
  `/apply-changes` carries this plan together with PLAN-LB-155, whose end-to-end check (`platform_runtime subagent dispatch --agent execution-context-level-3`) now
  also has a negative twin (`--agent plan-marshall:execution-context-level-3` answers the stem-naming miss).

## Follow-Ups

- **L3-4 (first-drift record order)** — recorded here, no plan. Trigger: a `drift_unchanged` stop on a plan whose previous drift return was interrupted before `set-phase 2-refine`.
  If the operator wants it closed, it is a one-sentence reordering in `execution-recovery.md` plus its doc-contract assertion; it would ride the next documentation plan.
- **L3-1, L3-2 (budget edge, mixed payload)** — recorded here, no plan; both are documented behaviour of a hard budget.
- **L3-5 (the 180 s figure repeated)** — recorded here, no plan.
- **Environment flakes** (`[Errno 39]` in the target-tree generator, the `test_executor_recovery.py` teardown timeout) — not caused by this plan; recorded here. If either recurs, it
  is an environment item for the operator's own queue, not a live-blockers plan.
- **Archived messages** `lessons-routing-090.md` and the PLAN-LB-155 follow-up origin stay as written.
