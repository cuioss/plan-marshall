envelope_version=1
sender_type=plan
sender_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
kind=landing
created=2026-09-24T16:20:18Z

## What landed

the-comment-pipeline-on-the-way-in shipped as #1616 (merged).

```landing-facts
schema=landing-facts/1
plan_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
pr=#1616
merge_state=merged
cleanup_owed=false
deliverables_total=10
deliverables_done=10
total_tokens=12215287
total_wall_seconds=96264.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.pre-submission-self-review.acceptance=operator_waived
```

## Residue

- Merged under a HEAD-bound `barrier-ask-override` at 4ebee67ec: required reviewer cuioss-review-bot was `participated_stale` (its last review predates the one-file indented-code fix). Operator ruled merge without re-review.
- PR #1612 was closed unmerged and re-opened as #1616 (CodeRabbit quota recovery); the create-pr step record was corrected from #1612 to #1616 at landing time.
- Pre-submission self-review closed under operator waiver after 7 rounds; finalize ran 9 loop-back iterations (ceiling 5, operator-overridden).
- Review retrospective: findings c108f6 and 61dc3e were filed after the last ingest pass, so their text lives only in `raw_input.body`; `is_status_summary` read the empty `body` and counted status note c108f6 as actionable (10 vs 9 by the counting rule). 61dc3e carries no responded stamp because its thread reply was posted via `ci pr thread-reply` directly.
