# Landing Analysis: PLAN-LB-100 — The merge path tells the truth: `pre_merge_gate merge` checks that every required review bot saw the head, a merge under an authorization is recorded as one, and the merge question says what follows

epic: live-blockers
workstream: WS-01
pr: #1883 (merge commit b399401ee33baac4972f083902292edad630d04a)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-100.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Grade: B. All three deliverables are met and the gate refusals are proven by mutation, but one acknowledged gap
remains in the very check the plan adds (the participation check binds to the provider's candidate, the merge to the
local head), the lane's self-review ended `budget-exhausted` with three items open, the landing is incomplete
(`total_tokens` unknown), and the run asked the operator a Sonar question the standing ruling says is never asked.

## Deliverable Fidelity vs Spec

Checked against the merge commit (`git show --stat b399401ee`: eleven files, +2571 −102, parent `6d1554570` which is the
LB-102 merge, so no skew), the PR read through the `ci` abstraction (state merged, merge commit as stated, the check list
read afterwards: `verify / verify`, `verify / gate`, `verify / conclusion`, `generate-check`, `dependency-review` all
success; CodeRabbit neutral, Sourcery skipped), and a content search on the merged tree for the new code.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `pre_merge_gate merge` runs the required-bot participation check against the candidate | shipped-as-specified, with a known limit | `merge_participation_unproven` exists in `pre_merge_gate.py` beside `merge_candidate_not_gated`; the landing and PR body name the refusal payload (`unproven_bots[]`, per-bot state, `roster_read`, `authorizable`), the HEAD-bound grant lookup, and no grant over an unreadable state. The limit is in Residue: the check proves participation against the provider's candidate, while the merge binds to the local head. |
| D1 an empty roster is not a pass, and the check says whether the roster was read | shipped-as-specified | Named tests per the landing (`..._empty_roster_is_refused_...`, `..._unreadable_roster_is_refused_...`); not re-run here. |
| D2 a merge under an authorization is recorded as one, by script | shipped-as-specified | `gap recorded` now occurs in `pre_merge_gate.py` (the spec's own check was "no `.py` file contains it at HEAD"); `record-merge` is the new verb; Branch A and E of `branch-cleanup.md` invoke it. The 47-character figure is pinned against the rendered string per the landing. |
| D3 every merge-path question tells the truth about what follows | shipped-as-specified | `consequence-text` renders the sentence from the knob. The site count is described two ways (the PR body says three option sites plus the red-CI prose; the landing says four sites including the rereview trigger prompt); both include the rereview and red-CI sites, and the census tests are said to be derived from the documents. I did not reconcile the two counts. |
| Standing constraint: quota-limited required bot with a qualifying review is admitted | shipped-as-specified | The landing records the mapping and an assertion against the predicate itself rather than a fixture (`test_the_participation_mapping_is_the_predicates_own`). |

Surface: the diff covers the declared `pre_merge_gate.py`, `branch-cleanup.md` and `test_pre_merge_gate.py`. It does not touch the
declared `review_completeness.py` (read for reuse only, as the spec's "(D1)" allowed). It adds `branch-cleanup-rereview.md`
(the D3 hypothesis site) and seven guard tests the new shape forced to change: three `test_participation_site_population_*`,
`test_step_records_facts_contract_facts`, `test_branch_cleanup_cleanup_owed_fact`, `test_lb55_merge_head_binding` and
`test_pre_merge_gate_refusal_category`. The spec's HYPOTHESIS entry for `manage-status` was refuted: the writer stayed
`mark-step-done`, called from the new verb. Under-declared surface: the guard tests (the spec did not know they pinned the old shape).

## Metrics and Anomalies

- Tokens: `unknown` — the OpenCode harness measured none; `inbox landing-check` reported `complete: false`
  (`missing_keys`: `total_tokens`). Out of scope under the focus rule.
- Evidence order: the landing states `mutation-after` for every deliverable and does not claim `test-first`. That is the honest label.
- Duration: first stamps on 2026-10-28 (a run spanning an evening and the next morning); the message is 2026-10-29T09:01:14Z.
- Anomalies: one daemon-routed build failed `execution_failed` (the worktree's `pwx` exited -1 before output) and every later build ran
  in-process; one server restart mid `wait-for-queue-settle`, after which the lane re-read its text and found it had changed under it
  (LB-102's worktree-first read); one guard refusal (a heredoc append, R1); the lane disclosed about three shell `ls` calls and a few
  `grep`/`sed`/`tail` calls as rule violations. Local `verify` had two whole-tree scanner timeouts under `-n auto`, green standalone;
  CI `verify / verify` is the authoritative run and is green.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `dcdcfb2dc` and `9c525c46e` (six findings fixed, one answered and accepted as
  a known-open limitation); two re-triggers were rate-limited. Sourcery (optional) refused twice on diff size (more than 150,000
  characters), never a gate. This is the settled standing-authorization case: a valid review exists, the quota blocks the re-review,
  moving on was correct and nothing here is raised as a question. The review history was taken from the landing and the PR body and
  was not re-read from the PR threads.
- CI/merge: merged through the merge queue; the parent of the merge commit is the LB-102 merge. Local `main` is at the merge commit
  and tracks `origin/main`.
- Operator questions: three. (1) open the PR with the three self-review items recorded; (2) the Sonar condition (see below); (3) the
  last cleanup step refused because the main checkout carried an unstaged `.plan/marshal.json` edit "this lane did not make".
  The third is an orchestrator-side collision, not a lane fault: that edit is the `sonar-roundtrip` lane-off change made in this
  session, left uncommitted in the shared main checkout while the lane was finishing. The lane stopped and asked instead of
  discarding it, which is correct behaviour. Inferred from the edit and its path, not read from the lane's own record.
- Sonar: `open_issue_count=unknown`, `open_issue_rules=unknown` (never `0`). The run asked the operator once whether to merge
  despite an undecidable Sonar read and was told to merge. That question should not exist: Sonar is not enabled for this project,
  yet `runbook_lane resolve` reports `sonar: configured` because `credentials_config.workflow-integration-sonar` is still in the
  tracked `.plan/marshal.json` and `default:sonar-roundtrip` was `lane: full`. The lane is faithful to a stale config. A note and a
  Watch, not a Sonar defect; the config fix is in flight separately (a chore branch, not yet landed).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-100 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-100 --field pr --value 1883`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-100 --field landing --value landings/PLAN-LB-100.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-100 --field plan_marshall_plan_id --value rb-lb-100-merge-path-truth`
- [x] epic.md narrative reconciled (merge-path half of the gate-truth item retired; review-policy half stays with PLAN-LB-101)
- [x] defects opened: incomplete landing (`total_tokens`); the LB-100 known-open items (medium, not staged)
- [x] Watches updated: the Sonar question recurs a second time (folded, not duplicated); the main-checkout collision; the routed-build failure with an unconfirmed trigger
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

Not verified here, and recorded as such: the per-landing session-database checks the anchor lists (restart count, guard-log lines by
session tree, read-class shell totals, edits outside the worktree, spoofed-identity prefixes). The landing's own claims on those
(one restart, one guard refusal, about three shell `ls` calls plus a few `grep`/`sed`/`tail`) stand as unverified leads. I also did not
re-run any test and did not read the pre_merge_gate diff line by line, so the behaviour claims in D1 and D2 rest on the named tests,
the landing's mutation runs and CI green, not on my own reading of the 1149 added lines.

## Follow-Ups

- **Known-open, accepted as out of scope on the PR (medium; not staged):** `_check_participation` proves participation against the
  provider's candidate while `_head_binding_refusal` binds the merge to the LOCAL head; the producer emits only a boolean
  `merge_candidate_sha_resolved`, so closing the gap needs a provider return-contract change. Until then the check can admit a head
  the bots did not see if the two diverge. CodeRabbit asked whether to open a follow-up issue.
- **Known-open, pre-existing and outside this plan:** the `state == merged` re-entry path documents `merge_mechanism` as unrecorded
  while Branch A/E make it mandatory, so that documented invocation would be refused `facts_incomplete`; the merge-queue reroute
  (`queue_wait: forbidden`) keeps knob-routed narration, so an operator on that reroute is told "rebase skipped" while the run
  dispatches `safe-merge`; the barrier's documented producer call places `--plan-id` differently from the new gate call (cosmetic).
- Self-review ended `budget-exhausted`: those three items were open at the round limit, and the operator chose to open the PR.
- PLAN-LB-101 is the review-policy half and now has its dependency satisfied. It shares `branch-cleanup.md` and the pre-merge-gate test
  surface with this plan; both are now on main, so LB-101's lane will read them as they are.
