envelope_version=1
sender_type=plan
sender_id=close-the-runtime-slice-parametrization
epic=test-quality
kind=landing
created=2026-09-09T07:25:43Z

## What landed

close-the-runtime-slice-parametrization shipped as #1455 (merged).

```landing-facts
schema=landing-facts/1
plan_id=close-the-runtime-slice-parametrization
epic=test-quality
pr=#1455
merge_state=merged
deliverables_total=8
deliverables_done=8
total_tokens=10806358
total_wall_seconds=84846.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.branch-cleanup.upstream_commit_count=2
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=6
step.create-pr.pr_number=1455
step.record-metrics.any_phase_missing_end_time=false
merge_commit_sha=9853a7ababf2aa87a59db1e36f2072680eeda96b
loop_back_iteration=3
```

## Residue

**The `steps` list carries 21 of the 23 composed steps.** `emit-landing` (order 1000) is the step
writing this message and `archive-plan` (1100) runs after it, so neither has a recorded outcome at
emission time. They are omitted rather than asserted — the derived-figure timing rule cuts both ways,
and a step's outcome written before the step ran would be a fabricated one.

**PLAN-155's D4 report figures, for the epic's ledger.** 97 files, all under `test/plan-marshall/**`;
+7143 / −7642 against the merge base (net −499), reported not targeted. Collected pytest items
20766 → 20954, monotonically non-decreasing at every one of eight measurements; skip count unchanged
at 8 throughout. Over-budget modules among the touched set 53 → 48, none newly over — reported only,
WS-04 owns the splits.

**Two spec deviations, both operator decisions.** (1) The cold read was widened from the spec's
sample to a full sweep: the 40-family sample surfaced 11 defects across 8 families, which made the
sample untrustworthy as a stopping point, and the full sweep then found 6 more families including a
second instance of the ids=-derived-from-a-foreign-object hazard. (2) The repair pass followed the
audit's findings rather than TASK-7's pre-computed step list — only 2 of the 8 flagged files carried
a repair step, so following the list would have left 6 known-defective files untouched.

**Three CodeRabbit nitpicks were deferred, not rejected.** Each needs a `marketplace/bundles/**`
production change, which PLAN-155's Expected Surface excludes and routes to WS-03 / WS-04 /
PLAN-130. Recorded as lesson `2026-09-08-21-001` with concrete remedies; the shared shape is *a test
mirroring a production set that production does not expose*.

**This run's lesson-shaped output went to the GLOBAL corpus, not this inbox.** The finalize
dispatcher forwarded `orchestrated: false` to `plan-retrospective`,
`project:finalize-step-review-retrospective` and `lessons-capture` without ever running the
item-4b.a0 resolution seam. The error was caught after those three had run and corrected before this
emission (the seam returns `orchestrated: true, epic: test-quality`). Consequence: 8
plan-retrospective lessons plus 2 appended recurrences are in `.plan/local/lessons-learned/` rather
than in `inbox/` as `kind: candidate-lesson` messages. They are recorded and not lost, but this epic
will not see them by draining. Recurrence appended to lesson `2026-09-06-07-002` (third instance).

**Sourcery reviewed nothing.** It refused structurally on every round — cap 150000 diff characters
against a measured 14971 changed lines. It is an optional bot so it blocked nothing, but the
participation quorum was satisfied over what is, in review-content terms, a single-reviewer PR.
`review_completeness` reports `proves: participation_only`.

**Five infrastructure defects were found and filed this run**, none of them PLAN-155's own subject
matter: `2026-09-08-22-001` (a bot publishing only an issue_comment can never satisfy
`head_sha_verified`), `2026-09-08-22-002` (`scope_creep_check` emits an unregistered finding type and
crashes at persist on every over-threshold plan), `2026-09-09-01-001` (the self-review surfacer
reported clean where CodeRabbit found three instances of a class it enumerates), `2026-09-09-01-002`
(a finalize loop-back never re-opens the metrics row — this run recorded `loop_back_iteration: 3`
while `generate` reported `re_entered_phases[0]`), and `2026-09-09-01-003` (phase-5-execute Step 10's
per-deliverable commit predicate tests the plan's chain tail rather than the deliverable's, so it
never fired and the orchestrator settled all 8 deliverables itself).
