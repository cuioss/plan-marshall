envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=landing
created=2026-09-13T08:36:45Z

## What landed

the-foreign-gate-population-and-branch-f-recovery shipped as #1473 (merged).

```landing-facts
schema=landing-facts/1
plan_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
pr=#1473
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=6965440
total_wall_seconds=434517.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.create-pr.pr_number=1473
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.cleanup_owed=false
step.branch-cleanup.work_performed=true
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=1
step.record-metrics.total_tokens=6965440
step.record-metrics.total_wall_seconds=434517.0
step.record-metrics.any_phase_missing_end_time=false
step.emit-landing.work_performed=true
merge_commit_sha=38af136ede5c7d6ea531a38d59a67ece1bf3ade2
```

## Residue

**Two review-pipeline defects were observed live on this PR and deliberately NOT fixed here.**
Both were resolved `accepted` as carry-forward to this epic, because fixing either would have
advanced HEAD and restarted the mandatory re-review cycle that had already cost three 90-minute
CodeRabbit quota waits on this run. They are two faces of one wrong assumption about how review
bots publish, and should be fixed together:

- `852b0f` (`automatic-review/scripts/review_completeness.py`) — the fresh-edit currency arm credits
  a thread ACKNOWLEDGEMENT as a fresh review. Observed returning `participation_complete: true` at a
  head where CodeRabbit's own walkthrough carried an explicit quota REFUSAL for exactly that delta
  and its coverage marker was one commit behind. A false green on a merge-gating predicate; the
  dispatch that hit it correctly refused to act on it.
- `658eec` (`workflow-integration-github/scripts/_github_pr.py`) — `pr wait-for-comments` samples each
  bot's NEWEST comment by creation time, so an in-place refusal EDIT of a persistent walkthrough is
  invisible. `rate_limited_bots[]` named only sourcery while CodeRabbit had refused. A caller trusting
  that list picks the wrong recovery (wait-for-silence rather than wait-for-window).

**One operator-directed in-PR scope expansion.** At the merge gate the operator directed one round of
pipeline fixes, which landed with failing-first tests: the `--measured-diff-size` argparse defect
(bare flag crashed the verb) and the `head_sha_verified` issue-comment defect (the issue-comment path
never ran the head-SHA check over the comment BODY). The second is what let this PR clear the
participation barrier at all.

**Producer gap the run could not mechanise.** `references.affected_files` recorded 14 of the 28 files
that actually landed, because scope moved during execute and nothing re-reconciles it. Every
`affected_files`-derived finalize step therefore under-scoped on this run. `reconcile-scope` already
detects this; nothing in finalize calls it.

**Cost signal.** 7.04M tokens with finalize at 75.1% — 5.4x the error anchor, the fourth consecutive
plan to miss it. The retrospective's conclusion is that the anchor measures the step roster rather
than the plans, and that re-tuning individual plans will not close it.

**Review reliability, observed.** 6 self-review rounds (9 findings: 8 fixed, 1 refuted) and 4
CodeRabbit rounds (5 actionable findings). Notably 3 of CodeRabbit's 5 inline findings were defects
in the fixes for its own earlier findings.
