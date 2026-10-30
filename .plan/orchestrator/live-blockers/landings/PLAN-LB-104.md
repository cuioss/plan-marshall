# Landing Analysis: PLAN-LB-104 — A routed build resolves the tree the caller named

epic: live-blockers
workstream: WS-04
pr: #1893 (merge commit 42b421ff2, merge queue, merge-group run 41027396799 success)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-104.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Grade **B**. Runbook lane, `deepseek-v4.1-flash/high`. The fix is in the source tree, which the main executor's
notation table points at, so a call through it and a lane worktree cut from the merge run it; the harness-installed copies (the lane
text of D3) carry it since the sync of 2026-10-30 (Claude cache 0.1.2041). D1 and D2 are in the merged code as specified; D1's live-record clause was not produced, and
the lane says so.

## Deliverable Fidelity vs Spec

Verified against the merged diff (`42b421ff2^..42b421ff2`: 13 files, 723 insertions, 19 deletions) and the PR's merge state. The
lane's failing-run claims (a named test red at a named commit) were NOT re-run by me and stand as the lane's own report.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 the submitted command names the tree the caller named, in absolute form | shipped-modified (one clause not met) | `_absolutise_project_dir` in `_build_execute_factory.py` rewrites both token forms (`--project-dir X`, `--project-dir=X`) onto `exec_root`, leaves every other token and a flag-less argv unchanged, and `_route_to_daemon` builds the command through it; the cwd-independence of `--plan-id`, `--working-dir`, `--env` and `--root` is argued in the code's own docstring. Routing tests added to `test_build_execute_routing.py`, a real-resolver test in `test_build_execute_factory.py`. The live-record clause is NOT met (below) |
| D2 a missing wrapper is a named failure, not an opaque `execution_failed` | shipped-as-specified | `_launch_fault_extra` carries `reason`, `wrapper` and `project_dir` onto a routed result; `_daemon_result_to_direct` and `_result_for_log_verdict` return the inner launch fault with exit -1 instead of `build_failed` with exit 1; `_build_format.py` whitelists the three fields; `_build_execute.py` and `_build_shared.py` carry the in-process leg |
| D3 the lane routes every build and never turns the server off for the rest of the run | shipped-as-specified | `runbook-lane/SKILL.md` diff read directly: default routing for every build, ONE in-process retry per launch fault with the next build routed again, a standing `in_process` only where `build-routing` answers it, the retry set taken from `_build_result.LAUNCH_FAULT_ERRORS`, and § 8 plus the progress-line template now name the per-`mechanism` build count; guard test in `test_runbook_lane.py` |

**D1's live-record clause is not met, and the cause is my spec.** The clause asked for a live routed build from a real lane worktree
with the relative form `--project-dir .plan/local/worktrees/{id}`. That value is relative to the main checkout, so it forces the main
checkout as the working directory, and from there the lane may run only the main checkout's executor, which is the base-commit
client without the fix. The branch's fixed client can only be exercised from the worktree, where the same tree is `.`. A done-when
that cannot be produced before the merge is a spec defect of the same class as the unshareable-SHA clause of PLAN-LB-58. The lane
recorded the pre-fix failure with the literal form (inner `execution_failed`, exit -1, rendered `build_failed`, exit 1) and four
post-fix routed runs from the worktree with the form `.`, and asked the operator, who chose to open the PR and report the clause
not met. That is the right handling; the report is accurate on this point.

**Surface reconciliation** (`inbox landing-check`, declared against realized): 7 declared entries, 13 realized paths, **6 added**,
0 declared and untouched, state `expansion_detected`. The six added paths are `build-server-client/SKILL.md`, the result-contract
document `extension-api/standards/build-execution.md`, `_build_format.py`, `_build_server_protocol.py`, `_build_shared.py`, and
`test_build_server_protocol.py`. Two are my spec errors: the rendered-failure hypothesis named `_build_result.py` as the place to
confirm, and the field whitelist that actually drops the reason is in `_build_format.py` (the lane confirmed this). The
`build-server-client/SKILL.md` edit was conditional in my "Adjacent to" line. **The lane's statement "no surface drift occurred:
every touched file is inside the spec's Expected Surface or is the result-contract document" is contradicted by the diff**: five of
the six added paths are neither. It reported no drift, so no drift question was put to the operator. No collision resulted: the plan
ran beside PLAN-LB-103, whose files it does not touch.

## Metrics and Anomalies

- Tokens: `unknown` (the landing carries no figure; token measurement is out of scope under the focus rule).
- Self-review reached its three-round limit (round 1: one blocker and 13 nits; round 2: five nits; round 3: two doc nits). The
  step is recorded `budget-exhausted`, with the D1 live-record clause as the open item.
- Anomalies the lane reports, not re-run: one `self-review` sub-agent ran a whole-tree build while the session was also building,
  against the lane's own "one routed build at a time per worktree" rule, and came back red on two tree-walking shape guards
  (pytest 300 s timeout under xdist). The same two guards timed out in the PLAN-LB-101 lane and pass in isolation. Serial whole-tree
  runs exceeded the 3600 s bound twice; the lane continued with the split form.

## Routing and Merge Behavior

- Review: CodeRabbit is required (`quota_limited`). The PR carries 16 formal reviews: nine by `coderabbitai` (03:20, 03:26, 03:26,
  03:27, 03:27, 05:16, 05:37, 06:19, 06:48 UTC on 2026-10-30), one dismissed Sourcery review at 03:56, and six by the lane's own
  posting account (its replies). A formal review exists on several heads. The lane records 4 + 3 + 1 findings over three reviewed heads, all fixed and
  answered. The merged head `d748e6c4e` is the commit that fixed the last finding; the standing authorization applies (a qualifying
  review, every finding handled, one re-trigger after the last push). Recorded as a note, not a finding. Sourcery is optional and
  hit its 7-day budget.
- CI/merge: merged through the merge queue; `pr queue-state` reads `pr_state: merged`, `merge_commit_sha: 42b421ff2`,
  `in_queue: false`, merge-group run `success`. The main checkout is at that commit, and the lane's worktree is no longer listed.
- Sonar: `n/a`, not enabled for this project.
- **Build routing — the lane's own count is NOT corroborated.** The lane reports 48 builds, all `mechanism=daemon_longpoll`, none
  in process, none degraded, no launch-fault retry. The daemon journal read for the lane's worktree root returns zero records, and
  the main checkout's journal holds nothing from that run. A live lane worktree does show its builds under its own root (the
  PLAN-LB-103 worktree: 107 records, all routed), so the empty read is most likely the removed worktree's rows not being retained,
  but that is an inference and the count stays the lane's own. What IS established: the code that stops the in-process cascade is in
  the merged source; whether it works against a live daemon from an installed executor is not yet evidenced beyond the lane's four
  worktree runs.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-104 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-104 --field pr --value 1893`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-104 --field landing --value landings/PLAN-LB-104.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-104 --field plan_marshall_plan_id --value rb-lb-104-routed-build-project-dir`
- [x] epic.md narrative entry for the landing; the `total_tokens` gap folded into it, out of scope under the focus rule
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **D1's live-record clause is open and can be closed now.** It needs one routed build run from the main checkout with
  `--project-dir .plan/local/worktrees/{id}`. No sync is needed: the main executor maps the build notation to the source tree
  (read from its notation table) and the main checkout is at the merge commit, so the merged client is what that call runs. I did
  not run it, because it builds inside another lane's worktree; no plan is staged for it.
- **The Maven hypothesis is not settled.** The lane did not read the other project's daemon journal, and D3's wording is
  symptom-based so it does not claim one cause. It stays an open decision of the epic, not a defect.
- **Not checked against the harness session database.** The lane's session-level counts (builds, retries, the concurrency
  violation, guard answers) are the lane's own, like the PLAN-LB-100, PLAN-LB-101 and PLAN-LB-102 landings.
- **Two tree-walking shape guards sit near the 300 s per-test timeout on a loaded machine** (also seen in PLAN-LB-101). A serial
  run is the reliable form. The host-load cause is addressed by the xdist bound (PR 1896, merged as edcdf9b8e, which replaces the closed PR 1895) and the
  slot cap of 2. Not a plan of this epic.
- **Surface under-declaration** of the shipped spec is not edited: the row is terminal, so the gate no longer reads it, and the spec
  stays as the record of what was declared.
- Fix-forward: none staged.
