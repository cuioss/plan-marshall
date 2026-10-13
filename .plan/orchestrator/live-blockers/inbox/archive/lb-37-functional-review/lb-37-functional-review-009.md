envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=landing
created=2026-10-13T13:54:53Z

## What landed

lb-37-functional-review shipped as #1759 (merged), the last part of a 5-PR stack (#1754, #1755, #1757, #1758, #1759).

```landing-facts
schema=landing-facts/1
plan_id=lb-37-functional-review
epic=live-blockers
pr=#1759
merge_state=merged
cleanup_owed=false
deliverables_total=20
deliverables_done=18
total_tokens=12262752
total_wall_seconds=335628.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,functional-review:done,code-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,plan-marshall:plan-retrospective:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:in_progress,archive-plan:pending
step.finalize-step-sync-baseline.action=merged
step.finalize-step-sync-baseline.upstream_commit_count=1
step.functional-review.may_close=operator_override
step.functional-review.acceptance=operator_override
step.code-review.may_close=operator_override
step.code-review.acceptance=operator_override
step.automatic-review.may_close=operator_override
step.automatic-review.acceptance=operator_override
step.create-pr.pr_number=1759
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.cleanup_owed=false
step.record-metrics.total_tokens=12262752
step.record-metrics.total_wall_seconds=335628.0
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- Post-landing follow-ups OWED (the 2 undone deliverables): TASK-26 / D10 — roll the change out to the 8 configured consumer repositories (marshall-steward upgrade onto functional-review + code-review); TASK-27 / D11 — switch the cuioss-review-bot settings repository to the code-review rulebook. Both tasks remain `blocked` by operator decision; they run after merge and harness sync (sync done in this finalize, registry repinned to 0.1.1916).
- Operator follow-up OWED: remove the marshall-steward `upgrade migrate-review-steps` migration in a later plan. Operator: "We said to migrate all clients afterwards. So the migration makes no real sense. Anyway, keep it but communicate to the orchestrator to remove the migration in one of the next plans again."
- Review closure by operator override: functional-review, code-review and automatic-review were closed by operator override at HEAD 31eb67a3c ("there are enough coderabbit reviews. Land now"); the merge went through under a barrier-ask-override merge authorization over review-barrier-gap (cuioss-review-bot participated_stale). The last commit (wizard-flow.md log path) was not re-reviewed by CodeRabbit (rate-limited).
- Landing shape: CodeRabbit's 100-file cap refused the original PR #1753 (198 files, closed unmerged), so the change landed as 5 stacked squash-merges: #1754 (part 1), #1755 (part 2), #1757 (part 3), #1758 (part 4a), #1759 (part 5 = 4b plus review fixes). Parts 1-4 were landed from a separate stack worktree under NO_PLAN and their review comments are not in this plan's findings store.
- Out-of-plan follow-ups recorded during review: the shell-quoting rule for free-text placeholders is applied only to functional-review.md / code-review.md; the other phase-6 workflows still double-quote placeholders (lesson 2026-10-13-07-002). Recording HEAD at the start of a review step (CodeRabbit N1 on #1755, declined) is open as lesson 2026-10-13-07-001.
- Retrospective sent 4 candidate-lesson messages (lb-37-functional-review-005..008): create-pr size-cap pre-check, stacked-landing footprint resolution, automatic-review structural-refusal escalation + cross-PR trigger-B filter, finalize record-step on re-fires.
