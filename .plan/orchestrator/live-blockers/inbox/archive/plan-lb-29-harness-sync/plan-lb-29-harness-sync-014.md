envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=landing
created=2026-10-09T14:14:15Z

## What landed

plan-lb-29-harness-sync shipped as #1724 (merged).

```landing-facts
schema=landing-facts/1
plan_id=plan-lb-29-harness-sync
epic=live-blockers
pr=#1724
merge_state=merged
cleanup_owed=false
deliverables_total=15
deliverables_done=15
total_tokens=16838118
total_wall_seconds=94828.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,ci-verify:done,plan-marshall:automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,finalize-step-preference-emitter:done,plan-marshall:plan-retrospective:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.work_performed=true
step.create-pr.pr_number=1724
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=2
step.pre-submission-self-review.acceptance=accepted
step.pre-submission-self-review.may_close=no
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- Merge commit on main is 35b5589b5ab6d007656c30cbf18e26332f9e3fec (squash, landed by the platform merge queue).
- `archive-plan` is written `pending` in `steps` because it runs after this message; it had not run when the facts were read.
- The pre-submission self-review did not close clean: six rounds (29 findings, all fixed), then closed by the operator at the round limit, so the fixes of commit b66aec620 were not re-reviewed in-house.
- The loop-back ceiling (max 5) was exceeded twice on explicit operator authorisation; the persisted counter ended at 7. Both extra rounds addressed CodeRabbit findings of one defect class (file operations following symbolic links): emitter output, source walk, install sync, repin. The plan scope grew by that class beyond the staged spec; the shipped PR body states it.
- The in-house review saw the install-sync destination-symlink write-through in its last round and did not file it; CodeRabbit filed it one round later (finding 7b7c8c).
- CodeRabbit's hourly quota refused the re-review of the first fix round twice; two 90-minute waits under the operator's standing policy preceded an accepted `@coderabbitai full review`.
- Sourcery (optional reviewer) refused the PR for diff size (cap 150000 diff characters; measured 15156 changed lines). cuioss-review-bot participated with an empty review on the final head.
- The registry repin was applied once at finalize at the operator's explicit direction although the machine-local `registry-repin` opt-in is disabled; the registry moved from 0.1.1886 (user scope) and 0.1.1875 (project scope) to 0.1.1888. The opt-in remains disabled, so the next finalize on this machine reports `behind` again unless it is enabled or the repin is applied by hand.
- A full session restart is required before a session loads 0.1.1888.
- `total_tokens` spans populations (dispatched plus one inline phase) and the 5-execute wall time absorbs finalize review rounds and the quota waits, because loop-back re-entries stamp no phase boundary.
- The retrospective wrote 13 candidate-lesson messages to this inbox (plan-lb-29-harness-sync-001 to -013); five further medium-confidence proposals are in the plan's quality-verification-report.md only.
- Known leftovers not addressed by this plan: check-then-act windows remain between the symlink checks and the writes (no no-follow open); `variant_emitter.py` writes level-variant agent files with a bare write when called directly; a version string containing a slash is checked for containment but not for an intermediate link; the lessons-housekeeping skill's Step 1 still names the retired `modified_files` read.
