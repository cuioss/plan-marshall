envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=truthful-signals
kind=landing
created=2026-09-25T13:31:02Z

## What landed

truth-179-opencode-target-detection-landed shipped as #1619 (merged).

```landing-facts
schema=landing-facts/1
plan_id=truth-179-opencode-target-detection-landed
epic=truthful-signals
pr=#1619
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=0
total_wall_seconds=148370.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:skipped,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,plan-marshall:automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
```

## Residue

Operator overrides applied during this run (all logged with evidence, evidence filed as process-compliance findings 001-005): pre-push-quality-gate whole-tree red overridden twice (pre-existing plugin-doctor rows + machine-speed module-tests timeouts; full Branch A green recorded 2026-09-25), push freshness overridden twice (narrow-scope success rows; verified basis on the second pass), self-review re-fire infra failures overridden twice (scoped sweeps clean). Still open for follow-up: `sync-antigravity` SKILL.md `mode:` value needs its author; durable fix to scope the gate's plugin-doctor sweep to tree sources; wrapper opacity when its parser yields nothing (fails closed AND blind).
