envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=landing
created=2026-09-13T12:37:45Z

## What landed

implement-plan-05-declaration-currency shipped as #1482 (merged).

```landing-facts
schema=landing-facts/1
plan_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
pr=#1482
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=0
total_wall_seconds=67052.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
```

## Residue

- The `create-pr` step record still names superseded PR #1478: that PR was
  closed unmerged during the CodeRabbit rate-limit recovery and replaced by
  PR #1482 for the same branch, which the platform merge queue merged as
  3a79a9a6af13cb66678a05ebbfbef2d99dfdc0b1. The `pr` fact above names the
  landed PR (#1482), not the stale record.
- `archive-plan:pending` in `steps`: archive runs immediately after this
  emission, so its outcome did not exist when the landing was written.
- Token totals are unmeasured on this target (no session transcript):
  `total_tokens=0` across 0/6 populations.
