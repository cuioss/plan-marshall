envelope_version=1
sender_type=plan
sender_id=domain-glob-seeding
epic=operator-ux
kind=landing
created=2026-09-04T15:49:28Z

## What landed

domain-glob-seeding shipped as #1406 (merged).

```landing-facts
schema=landing-facts/1
plan_id=domain-glob-seeding
epic=operator-ux
pr=#1406
merge_state=merged
deliverables_total=4
deliverables_done=4
total_tokens=12008583
total_wall_seconds=66568.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=2
step.create-pr.pr_number=1406
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

Items this epic should track that no step recorded as a fact:

- **Orchestration context was resolved late and wrong by the finalize orchestrator.** The item-4b.a0
  resolution belongs before the first lesson-emitting step; instead `orchestrated=false` / `epic=""`
  was assumed and forwarded to `plan-marshall:plan-retrospective` (995) and `default:lessons-capture`
  (991). Both therefore wrote to the GLOBAL lessons store rather than this epic's inbox as
  `kind: candidate-lesson`. The 13 lessons the retrospective recorded and the 1 merge lessons-capture
  performed are real and durable, but they are NOT in this epic's inbox and will not be drained here.

- **This PR merged with zero review substance.** All three configured reviewers produced nothing:
  `cuioss-review-bot` participated but filed no findings, `coderabbit` refused (quota, awaitable),
  `sourcery` refused (quota, hard, ETA ~3 days). The pre-merge barrier passed on PARTICIPATION only
  (`proves: participation_only`) and `review-retrospective` graded `indeterminate` by construction.

- **Scope addition outside the declared footprint.** `build.py` (commit 4e85bef) — a pre-existing
  quality-gate defect that hard-failed for any bundle with no test directory, verified reproducible on
  clean `main` before changing anything, fixed under explicit operator approval.

- **Three steps re-fired without a second `[DISPATCH]` emission** (`pre-push-quality-gate`,
  `pre-submission-self-review`, `automatic-review`, `finalize-step-simplify` — `firing_count: 2` each).
  The dispatch-audit check classifies steps, not firings, so it reported no gap.

- **`marshalld` was unreachable for the entire run**; every build degraded to in-process. It was
  `idle_and_stale` and was upgraded during the cache-sync step.
