# Landing Analysis: PLAN-LB-99 — A source checkout answers not_applicable instead of asking

epic: live-blockers
workstream: WS-04
pr: #1878 (merge 76adb7714, 2026-10-28)

> Landing record for one shipped plan. Grade B. Analysed from the inbox landing message
> `rb-lb-99-source-checkout-executor-skew-001.md`, then checked against the merged diff, the PR
> through the `ci` abstraction, the lane's progress file, `.plan/temp/guard.log` and the OpenCode
> session store (read-only, counts only).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a source checkout answers `not_applicable`, never `match` | shipped-as-specified | `runbook_lane.py` in the merge: `_EXECUTOR_SKEW_NOT_APPLICABLE`, layout `source_checkout`, `_is_source_checkout_bundle` (probed only after the versioned and flat legs decline), `_probe_is_running_lane_tree`, `_source_checkout_reason`; an unreadable executor stays `could_not_check`; a live version directory still wins |
| D2 — the lane text states every verdict | shipped-as-specified | `SKILL.md` § executor-skew names `match`, `skew`, `not_applicable`, `could_not_check`, says the new one proceeds without asking, states once why it is safe and what it does not cover (a stale executor template); section 0 and the landing rule-check line updated |
| D3 — proved the way a lane reaches it | shipped-as-specified | new `test_executor_skew_source_checkout.py` (353 lines): an end-to-end test through a really generated executor, with the mapping asserted; the executor-removed case answers `could_not_check` |

The outline decision was taken as option (a), an explicit `not_applicable` verdict. Option (b)
was rejected because `bootstrap` and `preflight` regenerate the shared executor in place, so neither
is a read-only witness. Option (c), leaving the question, was already ruled out. Both unverified
hypotheses in the spec are confirmed: a source checkout's lane text names no verb its mapped scripts
lack, and a stale executor template is not covered. The second is stated once in `SKILL.md`.

One pre-existing assertion was removed, `test_source_checkout_still_cannot_check`. It asserted the
behaviour this plan supersedes, and its coverage moved to the new module. The diff confirms the
removal and the replacement comment.

Declared versus realized surface: the merge touched four files. The realized set is `runbook_lane.py`,
`SKILL.md`, `test_executor_skew_flat_install.py` and the new `test_executor_skew_source_checkout.py`.
The spec declared the first three. It named `test_runbook_lane.py` (untouched, listed only as "stays
green") and three HYPOTHESIS surfaces that were not touched: `marketplace_bundles.py` and
`deployed_layout.py`, `generate_executor.py`, and `_flat_install_fixtures.py`. The new test module
was not declared. It collided with nothing, so no surface correction is owed.

## Metrics and Anomalies

- Tokens: the lane reported `total_tokens=unknown`, but the session store measured them. Parent
  session: 569,781 input, 65,852 output, 67,805 reasoning, 73,139,584 cache read. One child session
  (the self-review agent): 376,224 input, 11,862 output, 40,870 reasoning, 5,567,872 cache read. Tree
  total: 946,005 input, 77,714 output, 108,675 reasoning, 78,707,456 cache read. Cost recorded as 0.
- Duration: about 4 h 07 min wall clock (08:23Z to 12:30Z), most of it waiting on the CodeRabbit
  quota and the operator.
- Model: `deepseek-v4.1-flash`, variant `high`, in both sessions. This matches the landing's `model`.
- Restarts: none (`resume_attempts` 0 in both sessions; two user turns, the second being the "re-ask").
  One child session against the disclosed "dispatched once and continued once".
- Anomaly, **read-class shell calls under-disclosed**: the store holds 50 read-class shell calls
  across the tree (`grep` 35, `du` 5, `ls` 4, `tail` 3, `find` 1, `wc` 1, `command -v` 1) against the
  landing's disclosed 25 (`grep` ≈12, `ls` 4, `du` 4, `tail` 2, `find` 1, `wc` 1, `command -v` 1). The
  `grep` count is the large gap: 35 against about 12. Of the 16 shell calls in the child session, none
  was read-class.
- Guard log: three lines for the lane session, matching the disclosed three refusals, R1 (`du … | tail`),
  R7 (an Edit aimed at the main checkout, immediately re-issued in the worktree) and R1
  (`grep … | head`). The other 14 `|` characters in `grep` commands are regex alternation, not shell
  pipes. So the guard saw everything it can refuse, and plain `grep`/`ls`/`du`/`find` are not in its
  scope, which is the known blind spot.
- Chaining: two `git commit` calls with multi-line `-m` messages are single commands. No `&&`, `;` or
  `||` chaining anywhere.
- Spoofed-identity prefixes: none (no env-assignment prefix on any shell call; all 136 script calls
  are `python3 .plan/execute-script.py …`).
- Edits: every worktree edit used the worktree path; the one main-checkout path is the R7-refused edit.
  Writes outside the worktree are `.plan/temp/` and the `ci` body slots (17), as disclosed.
- Main checkout: clean; branch and worktree pruned. The shared main executor was not rewritten
  (modified 2026-10-27 21:16, before the lane started).

## Routing and Merge Behavior

- Review: CodeRabbit reviewed `5dd93eee7` (09:48) and `3264fd6d7` (11:03), then refused the later
  triggers on the rate limit. Sourcery reviewed `5dd93eee7`, `9fcaac8e4`, `3264fd6d7` and the merged
  head `33d613597` (11:35). All 7 review threads are resolved. The PR walkthrough reads as the
  landing states: CodeRabbit never produced a review of the final head. One valid CodeRabbit review
  exists, so the standing authorization applies; recorded as a note, not a question.
- CI/merge: CI green on `33d613597`, full `verify plan-marshall` green at four heads, merged through
  the queue as `76adb7714` with a single squash commit. The PR body still names `5dd93eee7` as the
  current head and lists the per-head runs only up to it, so it is stale against the merged head.
- Sonar: out of scope by the operator ruling of 2026-10-28; the lane's undecidable-read question
  and its two `unknown` Sonar keys predate the ruling and are not an anomaly here.
- Operator questions asked in the lane: three (executor-skew `could_not_check`, the Sonar gate asked
  twice). The first is the question this plan removes for a source checkout.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-99 --status shipped`
- [x] row `pr` stamped — `1878`
- [x] row `landing` stamped — `landings/PLAN-LB-99.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-99-source-checkout-executor-skew`
- [x] epic.md narrative reconciled: the incomplete-landing Open Defect for the missing `total_tokens`, and a recurrence note on the flat-install blind-spot defect
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- `total_tokens` stays `unknown` in the lane's landing while the store measures it. Recorded as the
  incomplete-landing Open Defect the verb requires; token and measurement work is out of scope under
  the focus rule, so nothing is staged.
- Read-class shell under-disclosure and the plain-`grep` blind spot: folded into the existing
  flat-install blind-spot defect as a recurrence; not staged.
- Sourcery's "text edited ahead of its script bypasses the guard" was answered, not fixed: a source
  checkout carries no version or stamp to witness it, and the failure is loud at the first unknown verb.
  No action.
