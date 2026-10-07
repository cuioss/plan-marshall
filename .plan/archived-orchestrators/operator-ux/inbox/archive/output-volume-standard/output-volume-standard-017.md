envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=landing
created=2026-09-03T16:12:40Z

## What landed

output-volume-standard shipped as #1387 (merged) — Rule 3 (output volume at phase
boundaries) authored into the user-communication standard, cross-referenced from
citations-only-return, and the persona SKILL.md enumeration re-counted.

```landing-facts
schema=landing-facts/1
plan_id=output-volume-standard
epic=operator-ux
pr=#1387
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=2902587
total_wall_seconds=32454.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:unknown
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.create-pr.pr_number=1387
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.upstream_commit_count=1
```

## Residue

- **archive-plan's outcome is structurally unobservable from this message.** This
  step runs at `order: 1000` and `archive-plan` at `1100`, so the landing can never
  carry that step's outcome. It is written `unknown` rather than an optimistic
  `done`; the epic should read the archived plan directory if it needs the answer.

- **The run was interrupted after the merge and resumed in a second session.** The
  first session completed through `plan-marshall:plan-retrospective` and then stopped
  with the phase still `in_progress`. The resume completed the tail
  (`lessons-capture` onward). Every step through `plan-retrospective` was skipped as
  settled rather than re-fired.

- **The push barrier's documented error default would have re-pushed a landed
  branch.** On resume, `git-workflow branch-sync-state` returned
  `status: error / head_unresolvable`, because `branch-cleanup` had already removed
  the worktree. The item-1 push re-entry contract says an error payload means
  RE-FIRE ("fail toward pushing"). That default is written for an *ambiguous* parity
  state; after a successful merge it is not ambiguous, and re-firing would have tried
  to resurrect a merged-and-deleted branch — exactly what the `remote_absent_landed`
  state exists to prevent. The skip here rested on independent evidence
  (`ci pr view` reporting `state: merged`, `merge_commit_sha 9fd0957`). Worth a
  contract look: `branch-sync-state` cannot reach its own `remote_absent_landed`
  verdict once the worktree is gone, so the one state that would have answered
  correctly is unreachable at exactly the point it is needed.

- **`lessons-capture` deviated from its single-staging-path prescription.** The
  workflow names one staging path (`work/inbox-payload.md`); with 11 messages the
  step used numbered variants in the same directory, because the Write tool refuses
  to overwrite an unread file. The prescription assumes one message per run.

- **Third recurrence of the sourcery false-participation gap** (priors
  `2026-08-25-09-012`, `2026-09-02-08-001`), and the third acceptance. Contained here
  only because sourcery sits in `optional_bots`. Filed as a candidate lesson; the
  remedy belongs in a plan owning `automatic-review/standards/sourcery.md`.
