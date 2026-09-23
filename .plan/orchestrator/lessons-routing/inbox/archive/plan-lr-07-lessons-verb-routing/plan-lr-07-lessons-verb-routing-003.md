envelope_version=1
sender_type=plan
sender_id=plan-lr-07-lessons-verb-routing
epic=lessons-routing
kind=landing
created=2026-09-23T06:58:49Z

## What landed

plan-lr-07-lessons-verb-routing shipped as #1584 (merged).

```landing-facts
schema=landing-facts/1
plan_id=plan-lr-07-lessons-verb-routing
epic=lessons-routing
pr=#1584
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=10457035
total_wall_seconds=113158.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.create-pr.pr_number=1584
step.branch-cleanup.merge_mechanism=merge_queue
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- Plan-efficiency budget: this run consumed ~8x the single_module+bug_fix error anchor (10.37M tokens vs 1.3M), 79% of it inside 6-finalize, driven by 8 loop_back_iterations of pre-submission-self-review plus 3 successive rounds of CodeRabbit re-review on the same TASK-4 fix. Two candidate-lessons on this were filed to this epic's inbox separately (plan-lr-07-lessons-verb-routing-001, -002).
- Scope widened mid-run by an explicit operator directive to lower `.plan/marshal.json`'s `phase-6-finalize.max_iterations` from 20 to 5, landed as a 4th file in this plan's footprint alongside the 3 declared files (100% recall on the declared set).
- `branch-cleanup`'s `merge_state` / `cleanup_owed` facts were backfilled after the fact (the merge-queue routing for this run was executed manually rather than through the step's own fully-scripted dispatch) — recorded as accurate but noting the provenance for anyone auditing this landing against the step's own execution trace.
