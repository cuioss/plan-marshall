envelope_version=1
sender_type=plan
sender_id=antigravity-execution-fidelity
epic=live-blockers
kind=landing
created=2026-10-14T21:37:58Z

## What landed

antigravity-execution-fidelity shipped as #1768 (merged).

```landing-facts
schema=landing-facts/1
plan_id=antigravity-execution-fidelity
epic=live-blockers
pr=#1768
merge_state=merged
cleanup_owed=false
deliverables_total=7
deliverables_done=7
total_tokens=unknown
total_wall_seconds=99386.0
harness=unknown
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,functional-review:done,code-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.functional-review.deliverables_met=7
step.functional-review.deliverables_met_with_residuals=0
step.functional-review.deliverables_not_met=0
step.functional-review.criteria_unevidenced=0
step.code-review.blocking_count=0
step.code-review.advisory_count=1
step.code-review.rules_cited=1
```

## Residue

- Token totals read `unknown`: transcript-less OpenCode target, no session identity; the unenriched gap flag is recorded, never a measured zero.
- One ledger row carries an invented commit suffix (self-reported in the decision log); it matches no real commit and is superseded by the correct row. The pure-append ledger offers no edit verb.
- CodeRabbit's Sorcery-size structural refusal (150000-char cap vs 4199-line diff) and the pre-merge barrier's clean pass are recorded in the step facts.
