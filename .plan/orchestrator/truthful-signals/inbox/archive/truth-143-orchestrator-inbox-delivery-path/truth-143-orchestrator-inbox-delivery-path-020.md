envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=landing
created=2026-09-20T08:40:00Z

## What landed

truth-143-orchestrator-inbox-delivery-path shipped as #1539 (merged) — the orchestrator inbox gained a real delivery path to a running plan, and its corpus instruments stopped publishing an unmeasured zero.

```landing-facts
schema=landing-facts/1
plan_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
pr=#1539
merge_state=merged
cleanup_owed=false
deliverables_total=10
deliverables_done=10
total_tokens=19921101
total_wall_seconds=219622.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:unknown,archive-plan:unknown
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=7
step.finalize-step-sync-baseline.work_performed=true
step.pre-submission-self-review.acceptance=accepted
step.pre-submission-self-review.may_close=yes
step.pre-submission-self-review.work_performed=true
step.create-pr.pr_number=1539
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.cleanup_owed=false
step.branch-cleanup.work_performed=true
step.record-metrics.total_tokens=19921101
step.record-metrics.total_wall_seconds=219622.0
step.record-metrics.any_phase_missing_end_time=false
step.verification-feedback.outcome=done
```

## Residue

- **A step that RAN is absent from the composed order.** `verification-feedback` executed twice (`loop_back` to `5-execute`, then `done` — "1 pr-comment finding resolved taken_into_account; 0 pending remain") but appears in neither `phase_6.steps` nor `candidate_steps`. It is inserted dynamically by the review-findings path, so the composed-order `steps` key structurally cannot carry it. Its outcome rides the optional `step.verification-feedback.outcome` key instead. The composed-order contract and the set of steps that actually run are not the same set, and `steps` alone under-reports the run.

- **`deliverables_done=10` hides an abandoned task.** All 10 deliverables completed, but the task roster is 28 tasks: 27 `done` and 1 `infeasible` — task 19, "Derive the mailbox checkpoint plan id from classification.plan_spec" (0/2 sub-steps), under deliverable 5 (D4, the check-points deliverable). A deliverable-level count reports this run as fully complete; the infeasible task is invisible at that granularity. D4's remaining tasks (8, 9, 21) did complete.

- **The two terminal steps' outcomes were not observable at emission time.** `emit-landing` is the step writing this message and `archive-plan` (order 1100) had not run, so nothing had been observed about either outcome when the payload was assembled. Both are written `unknown` rather than predicted as `done` — this is the derived-figure timing rule applied to a figure that cannot be settled by the producer, not a failed read. Expected settled values are `emit-landing:done` and `archive-plan:done`; the epic should read them from the archive record, not from this landing.

- **The run converged expensively, and the loop-back cost is not carried by any fact key.** `loop_back_iteration` reached 11. Firing counts: `pre-submission-self-review` 13 (9 of its 12 prior firings were `loop_back` to `6-finalize`), `finalize-step-simplify` 13, `project:finalize-step-plugin-doctor` 11, `project:finalize-step-lessons-housekeeping` 9. `push` recorded one `error` and two `failed` rows before succeeding. The 19.9M token total and 61h wall-clock are dominated by this re-entry, but no required key distinguishes first-pass cost from loop-back cost, so the totals read as the price of the work rather than the price of the convergence.

- **Producer-side contract note for this epic.** The dispatch that ran this step did not carry the `orchestrated` / `epic` runtime inputs the step body declares as dispatcher-resolved. Taking Step 0's guard literally would have emitted no landing at all immediately before `archive-plan` destroys the plan directory — a silent, unrecoverable loss of the hand-off. The epic was instead resolved from `request.md` `source_id` through the sanctioned detector (`orchestrator inbox detect` → `orchestrated: true`, `epic: truthful-signals`). The guard's fail-closed posture and the irreversibility of the next step point in opposite directions; that is a real gap in the step contract, not an operator error.
