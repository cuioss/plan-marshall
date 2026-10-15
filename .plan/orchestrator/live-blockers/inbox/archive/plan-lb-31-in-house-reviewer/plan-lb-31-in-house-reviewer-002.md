envelope_version=1
sender_type=plan
sender_id=plan-lb-31-in-house-reviewer
epic=live-blockers
kind=landing
created=2026-10-14T12:27:28Z

## What landed

plan-lb-31-in-house-reviewer shipped as #1771 (merged).

```landing-facts
schema=landing-facts/1
plan_id=plan-lb-31-in-house-reviewer
epic=live-blockers
pr=#1771
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=0
total_wall_seconds=68498
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,functional-review:done,code-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.functional-review.deliverables_met=5
step.functional-review.deliverables_met_with_residuals=0
step.functional-review.deliverables_not_met=0
step.functional-review.criteria_unevidenced=0
step.code-review.blocking_count=0
step.code-review.advisory_count=0
step.code-review.rules_cited=0
```

## Residue

- Measurement: 223 posted reviews (204 canned, 19 substantive); paired recall low single digits per side on both quality-claim repositories; fixed-diff experiment 8/8 triggered and 8/8 canned under the assembled charter; /improve zero suggestions; security cell populated once. Result document: doc/analysis/in-house-reviewer-efficacy.md. Dated tables, appendix and experiment comment list are in the PR description.
- Roster decision (operator): keep cuioss-review-bot required as is; CodeRabbit stays required; reopen condition not met. No roster file changed.
- Enrolment (TASK-6): recorded as NOT DONE — 0 of 13, 0 of 20. Gate: D3 decision keep-required-as-is plus no PLAN-LB-30 schema release evidenced. No probe PR opened, no /review posted for observation. PLAN-LB-20 may proceed only past its own decision and the schema release.
- Calibration registry now scopes the assembled-charter figure to the security Guide surface; the code-review Guide is UNVERIFIED by this measurement (adapted to upstream 187f7314 two-pass model at merge).
- Drift: 3 consecutive baseline_drift recoveries hit the loop cap; operator authorized the merge of origin/main (65b71aa1c) with the q4 reconciliation; loop then converged and landed via the merge queue as 7474b807.
