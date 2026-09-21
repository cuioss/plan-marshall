envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=landing
created=2026-09-17T02:41:43Z

## What landed

truth-166-architecture-refresh-migration-churn shipped as #1501 (merged) — `discover` now attributes descriptor deltas before committing them, and tool-migration churn has its own steward reconcile path.

```landing-facts
schema=landing-facts/1
plan_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
pr=#1501
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=9979683
total_wall_seconds=129600
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merged_sha=e8c3cad5b
step.pre-submission-self-review.rounds=4
step.pre-submission-self-review.findings_fixed=20
step.automatic-review.actionable_findings=7
step.project:finalize-step-sync-plugin-cache.daemon_reconcile=deferred
tasks_total=16
tasks_done=16
loop_back_iteration=6
```

## Residue

- The fix was exercised on itself: `discover --force --apply plan` during this plan's own finalize returned `attribution: clean`, `applied: none` and committed nothing.
- `finalize-step-simplify` edited three files outside the plan's declared footprint (`effort_pins.py`, `runtime_info.py`, `argparse_surface.py`) because `compute-footprint` resolves its base_ref against the LOCAL main. All three edits were reverted. This is the same attribution-scope defect class the plan fixes, one layer up, and it is not closed by this plan.
- `project:finalize-step-sync-plugin-cache` deferred the marshalld reconcile (daemon busy); a `reconcile-owed` marker persists on the developer machine.
- CodeRabbit refused once inside its rate window; the operator's unattended protocol was applied (1 wait of 10 spent, ~96 min) and the mandatory review completed across 3 rounds with 7 actionable findings, 0 false positives.
- 11 candidate-lessons were routed to this epic's inbox by `plan-marshall:plan-retrospective` (8) and `lessons-capture` (3); they are the narrative carry-out and are not restated here.
