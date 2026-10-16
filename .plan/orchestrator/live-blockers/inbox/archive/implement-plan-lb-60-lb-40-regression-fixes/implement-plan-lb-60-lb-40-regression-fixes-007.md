envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=landing
created=2026-10-16T10:39:29Z

## What landed

implement-plan-lb-60-lb-40-regression-fixes shipped as #1782 (merged).

```landing-facts
schema=landing-facts/1
plan_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
pr=#1782
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
total_wall_seconds=64859
harness=opencode
step.functional-review.deliverables_met=5
step.functional-review.deliverables_met_with_residuals=0
step.functional-review.deliverables_not_met=0
step.functional-review.criteria_unevidenced=0
step.code-review.blocking_count=0
step.code-review.advisory_count=3
step.code-review.rules_cited=3
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,functional-review:done,code-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:failed,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
```

## Residue

- `project:finalize-step-sync-plugin-cache` is recorded `failed` by operator direction: the documented `python3 marketplace/targets/sync.py` is refused by the repo R5 guard (direct interpreter path) and no executor/`pyproject` alias exists for the sync engine, so the harness installs were NOT synced from the regenerated `target/` trees. Operator action: run the sync out-of-context (or add an executor alias), then re-run finalize.
- `total_tokens` is `unknown`: this OpenCode harness exposes no session transcript, so `enrich` skipped on `no_session_id_transcript_less`. The wall total (18h) is idle-dominated.
- Four real defects were found by the in-run reviews and fixed before merge (extension_discovery partial-scan fail-open; upgrade-flow.md recovery path; the D4 version-split comparison via TASK-11; the CodeRabbit unreadable-bundle-root fail-open via TASK-12). `step.code-review.blocking_count=0` is the settled state; three advisory items remain un-actioned by design.
