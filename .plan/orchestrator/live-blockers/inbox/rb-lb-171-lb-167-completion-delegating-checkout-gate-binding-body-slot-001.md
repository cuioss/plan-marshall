envelope_version=1
sender_type=plan
sender_id=rb-lb-171-lb-167-completion-delegating-checkout-gate-binding-body-slot
epic=live-blockers
kind=landing
created=2026-11-20T08:22:52Z
revision=2
amended=2026-11-20T08:50:44Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-171-lb-167-completion-delegating-checkout-gate-binding-body-slot
epic=live-blockers
pr=#2033
merge_state=open
cleanup_owed=false
deliverables_total=5
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:blocked
unresolved_review_threads=0
review_body_findings_total=12
review_body_findings_handled=12
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

## Direction recorded (operator, this run)

The delegated branch of D1 is **descoped**: the check-run / job-graph machinery is to be removed, and D1 is to be reported NOT MET as written. The head-bound read licence, the mandatory carried-forward marking, the per-caller body slot and the document work stay. The delegating-consumer case is to be re-staged as its own plan, with the run-identity evidence the reviewers asked for (`thread_concern_remains` on `runbook_lane.py:2083`, and the three evidence-binding findings).

`deliverables_done` is therefore 4, not 5. The branch is **unchanged** at `1676d73c8` (green: `verify`, full `module-tests`, `quality-gate`, and the required CI checks); the PR stays open and unmerged.

## Descope inventory (mechanical, for the follow-up)

1. `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`
   - delete the whole "Delegated footprint rule" section — the block from the `# Delegated footprint rule …` banner through `_delegated_check_evidence` (the constants `_USES_LINE_RE`, `_PINNED_REF_RE`, `_NEEDS_OUTPUT_REF_RE`, `_JOB_ID_RE`, `_DRAFT_REF_RE`, `_REPO_SHAPE_RE`, `_PR_NUMBER_RE`, `_SPLIT_FOOTPRINT_SOURCE` and the functions `_delegated_workflow_spec`, `_called_workflow_jobs`, `_footprint_job_graph`, `_run_ci`, `_read_delegated_workflow`, `_read_pr_checks`, `_check_row_job_id`, `_local_path_veto`, `_delegated_check_evidence`);
   - delete the delegated `if` block in `_sonar_stale_delta_verdict` (the `delegated, delegated_reason = …` pre-read through the carried-forward return), leaving the local `_classify_paths` path as the only decision;
   - delete `--pr-number` from the `sonar-stale-delta` parser and its pass-through in `cmd_sonar_stale_delta`;
   - drop the `sys` import if it becomes unused (it was added for `_run_ci`).
2. `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md`
   - delete the "A consumer whose CI delegates its build" paragraph and the residual sentence it introduces;
   - drop `--pr-number {N}` from the `sonar-stale-delta` command in §6;
   - drop `delegated_*` from the refusal list in §6 and from §7's retry exemption.
3. `test/plan-marshall/runbook-lane/test_runbook_lane_sonar.py`
   - delete the module-level aliases `_REAL_DELEGATED_SPEC`, `_REAL_READ_DELEGATED_WORKFLOW`, `_REAL_READ_PR_CHECKS`;
   - delete the whole "a consumer that delegates its build to a reusable workflow" section (`_DELEGATED_REF`, `_DELEGATION_WORKFLOW`, `_CALLED_WORKFLOW`, `_checks`, `_repo_with_a_delegation`, `_patch_delegated`, every delegating test, `_REAL_CALLED_WORKFLOW`, `_real_checks`);
   - keep the "real-classifier twins" section (it exercises the local rule and needs no delegated code);
   - keep `_patch_delta`'s `_delegated_workflow_spec` stub only if the symbol survives — otherwise drop that line.
4. PR #2033 body: replace the D1 section with the descope note and set the evidence table's D1 rows to "descoped / not met as written".
5. Then: `verify` + `module-tests` + `quality-gate`, commit, push, re-run `review-gate` (the `thread_concern_remains` thread is about the removed branch, so the concern is moot; the bot's last word may still hold the gate, which is the operator's call), and only then the merge queue.

## What is already met (unchanged)

- **D2** — head-bound read licence (`--carried-forward-head-revision`, `analysed_revision_requires_verified_head`, `carried_forward_head_mismatch`) and the mandatory `--carried-forward` marker at `sonar-gate` and `sonar-facts`, with both heads in the facts.
- **D3** — per-caller body slot; the plan-less default slot refuses (`shared_body_slot_refused`); `land.md` names `land`; the lane names its plan id; the docs agree.
- **D4** — the lane no longer promises a retry for a refused stale read, states the cause the right way round, and §6/§7/§8 agree; the Sonar skill states the head-bound contract.
- **D5** — tests written red-first (20 + 9 + 3 failures at `a024fc8c2`), all green at the head; the twins included.
- **D1** — **not met as written** (descoped on the operator's word).

## Residue

- The descope above.
- The `thread_concern_remains` verdict on the attribution finding; it is about the code being removed, so re-running the gate after the descope should see a moot concern, but the gate keys on the reviewer's last word.
- The checks-read head binding, the non-four-space field indent, the run identity, the reverted-delta classification, the bounded `body_slot` and the mirrored body-verb tuple: all recorded, all tied to the descoped branch or to follow-up plans.
