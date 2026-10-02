envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=landing
created=2026-10-02T09:34:15Z

## What landed

cross-check-dated-archive-self-collision (PLAN-11) shipped as #1676 (merged, squash landing 8665ddacf on main).

```landing-facts
schema=landing-facts/1
plan_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
pr=#1676
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=6893138
total_wall_seconds=100575.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:failed,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:pending,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.work_performed=true
step.create-pr.pr_number=1676
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- `project:finalize-step-sync-plugin-cache` FAILED: its staleness guard reports bundles `plan-marshall-antigravity` and `plan-marshall-opencode` missing from `target/claude/` immediately after a successful `generate-claude` (1215 entries). The plugin cache was not synced, the on-main executor was not regenerated and the build daemon was not reconciled. The operator-only `--skip-staleness-guard` was not used.
- `emit-landing` and `archive-plan` read `pending` in `steps` because this message is written before either records its outcome.
- `pre-submission-self-review` is `done` by operator override after 4 rounds; the last round was not re-reviewed. On the final finalize re-entry the operator chose not to re-fire four steps the verdict-currency classifier marked invalidated (lessons-housekeeping, simplify, plugin-doctor at `4b13eefb8`, self-review at `c6537d168`, against the shipped `cff829d80`). Both rulings are in the plan's decision log.
- The first merge-queue attempt was dequeued by a red re-test: main had been broken by #1677 (`runtime.target=antigravity` in `.plan/marshal.json`), fixed by #1679. The landing gate recorded a `loop_back` (budget exhausted, PR `open`) because a dequeued PR also reads `open`.
- The sentinel (`NO_PLAN`) exclusion was never observed on a real plan store; it is covered by regression tests only. The self-snapshot exclusion was observed: `excluded_self_snapshots=[review-apparatus-26-09-21]`, `candidates_indeterminate` 93 (was 98), verdict still `false`.
- Accepted limitation: a four-group archive name whose other possible owner has no directory in either store root is read as the queried epic's own snapshot.
- The unified review triage was not dispatched (zero pending review comments) and the review retrospective ran inline on its zero-findings exit; its comparison grade is `indeterminate`.
- `total_tokens` spans populations (dispatched plus one inline phase) and excludes main-context spend on five phases; the billing-weighted total is 128,552,698.
- The retrospective routed 9 candidate lessons to this inbox (messages 001-009 from this sender).
