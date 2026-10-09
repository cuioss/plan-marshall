envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=landing
created=2026-10-09T10:03:31Z

## What landed

lb-23-verify-builds shipped as #1729 (merged through the merge queue as c9738952a80a5020c4ba258c2c9b0dae31a05672).

```landing-facts
schema=landing-facts/1
plan_id=lb-23-verify-builds
epic=live-blockers
pr=#1729
merge_state=merged
cleanup_owed=false
deliverables_total=9
deliverables_done=9
total_tokens=13122777
total_wall_seconds=50411.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.pre-submission-self-review.acceptance=operator_override
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- The pre-submission self-review did not converge: five rounds, 32 findings, all fixed, none pending. It was closed by operator decision and was not re-run on the commits made after the close (the CodeRabbit round-1 and round-2 fixes).
- `archive-plan` is listed as `pending` because this message is written before the archive move; it runs immediately after.
- The main checkout's `.plan/execute-script.py` was unusable after the move-back (`ModuleNotFoundError: plan_logging`): its bootstrap paths pointed into the removed worktree of another plan (`self-review-materiality`), and the plugin-cache self-heal did not recover. It was regenerated from the plugin cache before the worktree removal. The cause lies outside this plan (candidate-lesson 009 from this plan carries the detail).
- Not exercised by this plan: the real Windows path of the pytest temp-root owner probe; observing the new tests fail before the source change on deliverables 1, 2, 3, 4 and 6; a reviewer-noted window in which the build wrapper installs its signal handlers after the child process is started.
- CodeRabbit round-3 comment 944da6 was declined as a false positive but recorded `taken_into_account`; the review retrospective says it belongs on `rejected`.
- Main carries one unrelated commit (d5a6b2cd2, #1730) after this plan's merge commit; the recorded `merge_commit_sha` is c9738952a, not main HEAD.
