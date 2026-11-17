# Landing Analysis: PLAN-LB-154 — A conflicting baseline drift is reconciled onto the new base

epic: live-blockers
workstream: WS-01
pr: #2001 (https://github.com/cuioss/plan-marshall/pull/2001)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-154.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-154-conflicting-baseline-drift-recovery`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `13e2c72e2aba3ce719ed267ed1576fadb79d95b2` through the merge queue (queue run 43962272549). Message
`rb-lb-154-conflicting-baseline-drift-recovery-001.md` carries `total_tokens=unknown` (out of scope under the standing ruling) and
`self-review:clear` after four rounds (the fourth operator-approved).

## Deliverable Fidelity vs Spec

Corroborated against `origin/main` at the merge commit: the diff stat (8 files, 434 insertions) and a read of
`execution-recovery.md` § "Baseline drift recovery" and of the `git-workflow.py` diff.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a reconcile step between refine's return and the execute re-entry: rebase through the `git-workflow` verb, ledger remapped with the PLAN-LB-91 remap | shipped-as-specified | `execution-recovery.md` step 4 (re-read): fetch, record `{pre_sha}`, `worktree-rebase-to --base {base_branch}` (bare name, never a merge), branch on `status` then `action`, a `baseline_drift_reconcile` `pending:`/`done:` marker, conflict resolution under refine's per-path decision, the two-call `remap` with `unmapped` handling, `force-with-lease` publish. The spec's "rebase or merge" fork is settled as rebase |
| D2 an unchanged probe stops on the first repeat with a named reason | shipped-as-specified | the "Unchanged-probe stop" block (re-read) sits BEFORE step 1, stores `baseline_drift_probe` as `divergent_commits` `|`-joined plus `:` plus `conflict_count` (or `reconcile_status/reason` on the declined route), answers `error: drift_unchanged`, and the counter reset clears the recorded probe |
| D3 deferral text in `refine-workflow-detail.md` and `sync-with-main.md` | shipped-as-specified (lane-reported) | the two files are in the merged diff (8 and 9 lines); their text was not re-read here |

The spec's HYPOTHESIS (the probe can use `divergent_commits` plus the conflict file set) was refuted by the lane: the drift TOON carries
`conflict_count`, never a file list. The shipped signature uses the two fields that exist, and says why (`execution-recovery.md:15-17`, re-read).

**Scope additions beyond the spec's Expected Surface** (all re-read in the merge diff stat): `plan-marshall/workflow/execution.md` (the trigger
stub), `workflow-integration-git/scripts/git-workflow.py` (13 lines), `workflow-integration-git/standards/worktree-handling.md` (the 8-state row)
and `test_git_workflow_worktree_rebase_edges.py`. The `git-workflow.py` change is a real defect fix found by CodeRabbit, see L3-1.

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — the change centres on one prose procedure and one 13-line probe fix. By reading: no
build, no test run.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | OBSERVED: the old recovery logged, reset the phase, re-dispatched refine and re-entered execute with no ref move | checked | confirms | the new step 4 states the same sequence as its reason (`execution-recovery.md:52`) and the lane re-read it at base |
| L1-2 | OBSERVED: cap of 3, counter reset on any non-drift return | checked | confirms | `execution-recovery.md:179-196` carries both unchanged and extends the reset to the recorded probe |
| L1-3 | HYPOTHESIS: the probe is `divergent_commits` plus the conflict file set | checked | refutes | the TOON carries no file list (`sync-with-main.md` step 6, per the lane); the shipped signature is `divergent_commits` plus `conflict_count` |

**Layer 1 verdict:** no refuting finding against a spec claim that the plan relied on; the one refuted hypothesis was handled in the design.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file | Verdict |
|-------------|------------|--------------------|------------------|---------|
| D1 | `execution-recovery.md` step 4.1 to 4.5 and step 5 | doc-contract tests in `test_baseline_drift_recovery.py` (pre-fix run: 3 failed, per the lane) | none | checked |
| D2 | the unchanged-probe block, `:15-29` and `:196` | `test_unchanged_probe_stops_on_the_first_repeat` (pre-fix run: 1 failed, per the lane) | none | checked |
| D3 | `refine-workflow-detail.md`, `sync-with-main.md` | two doc-contract tests (pre-fix run: 2 failed, per the lane) | none | not re-read |
| scope addition | `git-workflow.py` `cmd_worktree_rebase_to` conflict probe | `test_git_workflow_worktree_rebase_edges.py` stages a real `git worktree add` checkout; the lane records a `mutation-after` run (job log named) | `worktree-handling.md`, `execution.md` | checked |

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `git-workflow.py` `cmd_worktree_rebase_to` (merged diff) | a real rebase conflict in a linked worktree (every plan worktree) | before the merge, the probe looked through `target/.git`, a pointer FILE in a linked worktree, so a real conflict answered `error: rebase_failed` with the rebase left in progress; now `rev-parse --absolute-git-dir` resolves the state directory and the answer is `status: conflict`. The recovery's conflict route could not have run without it. Re-read: the change falls back to `target/.git` when the resolve fails | fixed in the plan (info) |
| L3-2 | `execution-recovery.md:15-29` | the FIRST drift return of a plan, when no probe is recorded | the text says what an equal and a different signature do; the absent case reads as "different" and records, but is not stated | minor, documentation |
| L3-3 | `execution-recovery.md` step 4 | an agent executing a ~150-line, four-level-nested prose procedure | the procedure is long enough that a skipped sub-step (the 4.2a marker, the executor refresh after a continuation) is the likeliest failure; the doc-contract tests pin that the text names each part, not that an agent follows it | info, not shown by reading |
| L3-4 | `finalize-step-sync-baseline.md:38`, `branch-cleanup.md` | `worktree-rebase-to` now answers `status: conflict` where it answered `error: rebase_failed` | the lane says both callers handle `conflict`. Re-read for `sync-baseline`: its intro records `outcome=failed` and halts on a conflict. `branch-cleanup` not re-read | info, lane-reported for one of two callers |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (the lane reports 34010 tests at the last head), the
mutation runs, and the unchanged-probe stop under a real second drift return. No run was made here.

**Layer 3 verdict:** no blocker, no major. L3-1 is a behavioural fix inside a documented-as-documentation-only plan; the lane reported it.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only | conforms | the new prose states the present procedure; no history clause |
| `pm-dev-python:python-core` | explicit exception handling, no bare `except` | conforms | the probe fix tests `rc_gd == 0` and falls back, no exception handling added |
| CLAUDE.md Workflow Discipline | no shell file operations | deviates (self-reported) | `ls -a .plan` and `tail -n 25` on a build log; the guard refused one `find ... | head` for shell chaining. The retained guard window carries no line attributable to the run, so "all kept" is not claimed |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: CodeRabbit refused twice for quota before accepting (the lane waited 90 minutes twice, escalated once to a full review); 17 builds, all
  `daemon_longpoll`, one `verify` hit the explicit 1275 s bound and was run in split form; sourcery refused on its 7-day budget (optional).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited, `review_complete_after_handling`) reviewed `5c043d744` (5 findings) and `3844433c9` (1 finding), all fixed and
  replied; the standing authorization was not needed. Not independently re-run here.
- CI/merge: green on the pushed heads per the lane; queue merge.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-155 and -157 on declared-disjoint surfaces; it merged after PLAN-LB-153 and both edited `execution.md`, which the
  base merge resolved cleanly (the spec had said "none staged" for overlaps, true when staged).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-154 --status shipped`
- [x] row `pr` stamped — `2001`
- [x] row `landing` stamped — `landings/PLAN-LB-154.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-154-conflicting-baseline-drift-recovery` (from the sender)
- [x] `epic.md` narrative: one Decision bullet for the two landings
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- No executor regeneration is owed (a verb's internal probe changed; the executor maps scripts). A harness sync is owed for the edited bundle sources.

## Follow-Ups

- **L3-2 (first-return wording)** — staged as PLAN-LB-159 D1 (a documentation sentence naming the no-recorded-probe case, pinned by the doc-contract suite).
- **L3-4 (callers of `worktree-rebase-to`)** — closed on the follow-up read: `branch-cleanup.md:432` handles `status: conflict` by aborting cleanup and logging the `conflicts[]` list, as `finalize-step-sync-baseline` does.
- **Behavioural note for operators:** a conflict in a linked worktree now answers `status: conflict` from `worktree-rebase-to` instead of `error: rebase_failed`.
  A consumer script that matched the old error token for that case would no longer see it; none is known in this repository.
- **sourcery** stays quota-blocked for about two days; optional, nothing owed.
