envelope_version=1
sender_type=plan
sender_id=git-branch-mechanics
epic=finalize-machinery
kind=landing
created=2026-09-17T20:15:19Z

## What landed

git-branch-mechanics shipped as #1509 (merged).

```landing-facts
schema=landing-facts/1
plan_id=git-branch-mechanics
epic=finalize-machinery
pr=#1509
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=0
total_wall_seconds=38313
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:skipped,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
```

## Residue

- Both PLAN-04 defects fixed and verified: branch-sync-state reaches
  `remote_absent_landed` via the main-checkout fallback probe (merged-and-deleted
  branches map to push `skip`), and prune-local-and-remote-ref tolerates an
  already-deleted local branch while still pruning
  `refs/remotes/origin/{branch}`. Four regression tests added; branch-cleanup
  ordering contract updated. Merge commit f8b0fa40.
- Bot review added real value: 8 actionable CodeRabbit comments produced
  TASK-4 through TASK-8 (exit-code discrimination on both prune guards,
  feature-tip preservation, non-directory-worktree fallback, success-definition
  wording), all fixed and green; 1 suggestion declined with rationale.
- Lesson 2026-09-04-14-005 retired as completely covered (tombstoned with
  clause + input evidence).
- Operator waivers on record: finalize ran without session identity
  (telemetry-only input, absent on this runtime; filed as epic finding
  git-branch-mechanics-002.md), and self-review was closed after two
  identical accepted-clean rounds on a deterministic surface when the
  verifier twice held close on incurable grounds.
- Incident worth noting: the main-checkout executor went stale after the
  merge (embedded pre-fix scripts), so the first post-merge prune ran the
  old abort path; regenerated via generate_executor and the retry took the
  tolerated path. The stale-executor class is a recurrence risk for any
  post-merge verb run from main.
- Metrics carry 0 tokens: OpenCode target exposes no usage capture
  (known gap); wall time 10h38m across 6/6 closed phases, 8/8 tasks done.
