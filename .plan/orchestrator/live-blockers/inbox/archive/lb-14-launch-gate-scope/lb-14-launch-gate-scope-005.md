envelope_version=1
sender_type=plan
sender_id=lb-14-launch-gate-scope
epic=live-blockers
kind=landing
created=2026-10-08T14:57:12Z

## What landed

lb-14-launch-gate-scope shipped as #1715 (merged).

```landing-facts
schema=landing-facts/1
plan_id=lb-14-launch-gate-scope
epic=live-blockers
pr=#1715
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=9457242
total_wall_seconds=26023.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.work_performed=true
step.create-pr.pr_number=1715
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=1
step.pre-submission-self-review.acceptance=accepted
step.pre-submission-self-review.may_close=no
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- The `emit-landing` and `archive-plan` entries in `steps` are written as `done` by this message's own producer before those two records exist; every other entry is transcribed from a recorded step outcome.
- `pre-submission-self-review` fired nine times and passed its five-round limit twice. It was closed by operator decision (`may_close=no`), and the last fix commit (4d5eb641a, the follow-up to the unreadable-footprint fix) was not re-reviewed by that step.
- One review-bot comment led to a post-PR behaviour fix: a live plan whose captured footprint cannot be read now stays indeterminate and blocks, instead of being treated as having no footprint yet (commits 5d6bf6b14 and 4d5eb641a).
- Sourcery (optional reviewer) refused the diff on size (cap 150000 diff characters, measured 3182 changed lines). Both required reviewers took part; cuioss-review-bot published a review with no findings.
- One file shipped beyond the outlined set: `plan-orchestrator/templates/plan-spec.md`, a wording correction made under the operator's "fix all sites" decision.
- The plan retrospective routed four candidate lessons to this inbox (lb-14-launch-gate-scope-001 to -004).
- Merge-commit on main: 3fe828c84633c65b86ec9bd6a086132fecc652c9.
