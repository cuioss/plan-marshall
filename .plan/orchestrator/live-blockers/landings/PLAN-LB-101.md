# Landing Analysis: PLAN-LB-101 — The barrier states and enforces the review policy

epic: live-blockers
workstream: WS-01
pr: #1890 (merge commit 993423ac5, merge queue, merge-group run 40985915285 success)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-101.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Grade **B+**. Runbook lane, `deepseek-v4.1-flash/high`, one lane session tree (`ses_e7873f394ffeL6aXYr4HIleVO4`). The fix is in
source only until the next harness sync.

## Deliverable Fidelity vs Spec

Verified against the merged diff (`993423ac5^..993423ac5`: 33 files, 1589 insertions, 236 deletions) and the PR's review and
merge state. The lane's evidence labels were read against the diff; its failing-run claims (a mutated source failing a named
test) were NOT re-run by me and stand as the lane's own report.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 an unreadable roster is an error, never an empty roster | shipped-as-specified | `review_completeness.py` and `automatic-review/SKILL.md` changed; new `test_roster_read_failclosed.py`; the barrier's own read in `pre_merge_gate.py` follows the same contract |
| D2 a stale required bot is re-triggered before the barrier asks, and the question says so | shipped-as-specified | `pre_merge_gate.py`, `branch-cleanup.md`, `github_re_review.py` changed; pinned in `test_review_policy_defaults.py`; the lane placed the trigger in the barrier and not in the leaf, with the reason (one trigger per head) recorded |
| D3 no shipped document or generated option demotes a required bot | shipped-modified | scanner `_required_bot_demotion_scanner.py` and `test_required_bot_demotion_contract.py` are new; the four cited sites changed; scope grew to five more documents (below) because the demotion offer was also in `plan-marshall/workflow/execution.md` and the structural-refusal docs |
| D4 a quota refusal on a required bot is waited out by default | shipped-as-specified | `test_config_defaults.py` diff read directly: `review_rate_window_await` `False` → `True` and `review_rate_window_timeout_seconds` `3600` → `5400`; `merge_lock.py` changed with the rate-window tests; the policy numbers (90 minutes, ten) won over the old defaults (3600 s, six), with the reason recorded |

**Surface reconciliation** (`inbox landing-check`, declared against realized): 8 declared entries, 33 realized paths, **17 added**,
1 declared and untouched (`test/plan-marshall/phase-6-finalize/`), state `expansion_detected`. The 17 added paths are the
documentation ripple of D3 (`doc/user/configuration.adoc`, `doc/user/parallelism-and-locking.adoc`, `bot-participation-contract.md`,
`cuioss-review-bot.md`, `sourcery.md`, `manage-locks/SKILL.md`, `phase-6-finalize/SKILL.md`, `execution.md`,
`pr-review-operations.md`, `workflow-integration-github/SKILL.md`, `automated-review-lifecycle.md`), the barrier script
`pre_merge_gate.py`, the re-review script `github_re_review.py`, and four tests whose old defaults changed. This is a spec error of
mine: the spec put `bot-participation-contract.md` out of scope in an "adjacent, does not change" line although D3 required changing
the demotion text it carries, and it declared no documentation. The lane reported the drift and the operator chose "continue,
record the drift". No collision resulted: the plan ran beside PLAN-LB-103 and PLAN-LB-104 and none of their files is in this diff.

## Metrics and Anomalies

- Tokens: `unknown` (the landing carries no figure; token measurement is out of scope under the focus rule).
- Duration: the first daemon job was submitted 2026-10-29 12:21 UTC and the landing message is stamped 2026-10-30 05:34 UTC, about 17 h.
- Self-review reached its three-round limit (round 1: 20 findings, one blocker; round 2: six; round 3: only the record-level spec-surface item). The step is recorded `budget-exhausted`.
- Anomalies: two whole-tree scanner tests in `test_harness_shape_guards.py` timed out locally (pytest-timeout above 300 s) with the host load average near 198, in a module this plan does not touch. They pass in isolation and CI's `verify` ran green.

## Routing and Merge Behavior

- Review: CodeRabbit is required (`quota_limited`). The PR carries 41 formal reviews, about 20 of them by `coderabbitai` (the first 2026-10-29 16:38 UTC, the last 2026-10-30 00:37 UTC), so a formal review exists on several heads. The lane records 22 findings over eight rounds, all fixed or answered. Its quota refusals (six, the last "next included review in 38 minutes") are on the PR as the lane states. The merged head is one commit past the last reviewed head and that commit is the fix CodeRabbit asked for. The standing authorization applies; recorded as a note, not a finding. Sourcery refused on size and is optional.
- CI/merge: merged through the merge queue; `pr queue-state` reads `pr_state: merged`, `merge_commit_sha: 993423ac5`, `in_queue: false`, merge-group run `success`. The lane states the worktree was removed with a clean status and the main checkout fast-forwarded to that commit; main was at that commit when I read it.
- Sonar: `n/a`, not enabled for this project; no figure collected.
- **Build routing:** the lane's first routed `module-tests` failed with an empty nested log (`pwx module-tests`, exit -1 at 0 s) and every later build ran `--execution-mode in_process`. The daemon journal for the lane's worktree root shows exactly ONE job, a failure after 1 s, and nothing after it, so the account is exact. This is the trigger PLAN-LB-104 fixes (a relative `--project-dir` re-resolved against the worktree). The consequence is the larger finding: after the first failure all builds of this lane ran outside the daemon, so they were not counted against the slot cap, which is what the host-load figure of about 198 reflects. See the Follow-Ups.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-101 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-101 --field pr --value 1890`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-101 --field landing --value landings/PLAN-LB-101.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-101 --field plan_marshall_plan_id --value rb-lb-101-review-policy-barrier`
- [x] epic.md narrative entry for the landing; the incomplete-landing defect (`total_tokens` unknown) folded into it, out of scope under the focus rule
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **Not checked against the harness session database.** The lane's session-level counts (two guard refusals, one question, restarts, read-class shell calls) are the lane's own and are not corroborated here, like the PLAN-LB-100 and PLAN-LB-102 landings.
- **In-process builds bypass the build-slot cap.** This landing is the matched case for the host out-of-memory kills of 2026-10-25 to 2026-10-30: a lane that fell back to in-process after one routed failure ran uncapped pytest sessions, each with one xdist worker per CPU thread. Two fixes are in hand and neither is a plan of this epic: the machine-global slot cap was set to 2, and PR 1896 bounds the xdist worker count of module-tests and coverage (merged as edcdf9b8e; it replaces the closed PR 1895). PLAN-LB-104 removes the routed failure that causes the fallback.
- **Surface under-declaration** of the shipped spec is not edited: the row is terminal, so the gate no longer reads it, and the spec stays as the record of what was declared.
- Fix-forward: none staged.
