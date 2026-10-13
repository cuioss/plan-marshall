envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=landing
created=2026-10-11T16:02:52Z

## What landed

lb-25-phase-and-merge-gates shipped as #1751 (merged via the GitHub merge queue as 3ff307ddd).

```landing-facts
schema=landing-facts/1
plan_id=lb-25-phase-and-merge-gates
epic=live-blockers
pr=#1751
merge_state=merged
cleanup_owed=false
deliverables_total=10
deliverables_done=10
total_tokens=14267696
total_wall_seconds=135010.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.pre-submission-self-review.may_close=operator_override
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- Accepted residual (operator decision at the self-review round cap, findings bc5abc / 2e71e5): merge-lock ownership is keyed on plan_id, not session. A second concurrent finalize session for the same plan can be admitted as already_held and release the first session's lock; and branch-cleanup.md's landing-gate failure path runs merge_lock release while not holding the lock after an unobserved enqueue. Follow-up owed: session-scoped lock ownership.
- Pre-submission self-review spent its full 5-round budget; each round on the merge-lock / integrate_into_main lifecycle surfaced a new real defect (fixed in TASK-21/22/23 and loop-back fix commits).
- Open low-severity advisories not fixed: GitLab merge-train F1 loop_back re-fires branch-cleanup immediately while the MR is still on the train (D6 semantics); Branch C prose "Nothing was rebased" after an early-hold rebase; docstring gaps around the raised-acquire path in integrate_into_main.
- 11 candidate-lesson messages were filed to this epic's inbox by plan-retrospective (lb-25-phase-and-merge-gates-001..011).
- Main checkout has an uncommitted uv.lock re-lock from the post-merge target regeneration (caused by main's ruff/mypy pyproject bumps, not by this plan).
