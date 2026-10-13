envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=landing
created=2026-10-10T11:59:52Z

## What landed

lb-24-review-step shipped as #1742 (merged, squash 7dd1d34338f1fcc3b14c3835ac028156b3f1c8c8, via the merge queue).

```landing-facts
schema=landing-facts/1
plan_id=lb-24-review-step
epic=live-blockers
pr=#1742
merge_state=merged
cleanup_owed=false
deliverables_total=11
deliverables_done=11
total_tokens=15575396
total_wall_seconds=143775.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.pre-submission-self-review.may_close=operator_override
step.create-pr.pr_number=1742
```

## Residue

- pre-submission-self-review used all 5 fix rounds and was closed by operator decision; it was closed again by operator override at 8fc4ed521 and c6571e103. The review-fix commits after the first close (fix tasks 23, 24, 25 and the inline review edits) were built and CI-verified but not self-reviewed; CodeRabbit reviewed them.
- Live-PR evidence still owed from the plan spec: the CodeRabbit quota-recovery path did not recover on its own on this PR. The selector answered settle_stale_notice for a notice whose window had already elapsed, and the main context waited and posted `@coderabbitai full review` by hand (twice). The in-house reviewer's `/review` on re-entry worked.
- New defects observed on this PR in the area the plan changed, filed as candidate lessons by plan-retrospective: re-review credits CodeRabbit's "review in progress" summary as a finished head-verified review; the "Full review triggered/finished" acknowledgment is filed as findings (case-sensitive pattern).
- Plugin registry was repinned to 0.1.1895 by a one-off operator-approved apply; the registry-repin opt-in stays disabled on this machine.
- The lessons corpus was found emptied mid-finalize (69 active, then 0); no log names a cause. Filed as a candidate lesson.
