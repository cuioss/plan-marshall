envelope_version=1
sender_type=plan
sender_id=truth-161-adr-number-allocation
epic=truthful-signals
kind=landing
created=2026-09-22T22:17:47Z

envelope_version=1
sender_type=plan
sender_id=truth-161-adr-number-allocation
epic=truthful-signals
kind=landing
created=2026-09-22T22:14:53Z

## What landed

truth-161-adr-number-allocation shipped as #1586 (merged).

```landing-facts
schema=landing-facts/1
plan_id=truth-161-adr-number-allocation
epic=truthful-signals
pr=#1586
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=0
total_wall_seconds=26855.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:n/a
```

## Residue

- pre-submission-self-review first fired against a stale local base
  and failed closed, then passed clean on retry after the base was
  fast-forwarded (15 candidates, no findings).
- ci-verify timed out twice while remote CI was still running, then
  recorded green on the completed run; no code defect was involved.
- The pre-push gate picked up three one-line ruff-format blank lines
  in unrelated permission-fix split tests and committed them as a
  style commit on the branch.
- Review loop-back added two fix tasks beyond the planned five:
  malformed ADR filenames no longer collapse to duplicate number 0,
  and the duplicate scan gate is now wired into branch-cleanup before
  merge or queue enqueue.
