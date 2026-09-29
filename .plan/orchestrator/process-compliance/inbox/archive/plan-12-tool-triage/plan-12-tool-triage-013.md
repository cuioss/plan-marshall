envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=landing
created=2026-09-29T13:42:10Z

## What landed

plan-12-tool-triage shipped as #1653 per its create-pr record (merged).

```landing-facts
schema=landing-facts/1
plan_id=plan-12-tool-triage
epic=process-compliance
pr=#1653
merge_state=merged
cleanup_owed=false
deliverables_total=6
deliverables_done=6
total_tokens=18462076
total_wall_seconds=170910.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:pending,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.pre-submission-self-review.may_close=operator_override
```

## Residue

- The create-pr record's `pr_number` fact is stale: it names #1653, but #1653 was closed and replaced by #1654 (CodeRabbit close-and-reopen recovery). The PR that actually merged is **#1654**, squash-merged by the platform merge queue as `26f864b1eec66eeb1b663e75d08826c573b877e0`. Transcribed as recorded per the payload spec; the contradiction is operator narrative (candidate lesson plan-12-tool-triage-012 covers the restamp defect).
- pre-submission-self-review was closed by operator override (no clean full-scope may_close=yes pass) after 12 finalize loop-back iterations, 7 beyond max_iterations=5, each operator-authorized. The last full pass returned 2 contract_drift findings, both fixed (24f7fb3c7, dd28b5002) but not re-verified by a further self-review round.
- main was merged into the branch (7c2800c85) to resolve a content conflict with #1651 in plan-retrospective/SKILL.md (path rename only), after which CI, one review round, and the pre-merge barrier re-ran clean.
- Post-merge triage correction: finding 63a935 (cuioss-review-bot) moved taken_into_account -> rejected; review-retrospective.md predates the correction.
