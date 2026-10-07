envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=landing
created=2026-09-24T09:07:31Z

## What landed

ledger-decomposition-and-row-vocabulary (PLAN-02) shipped as #1609 (merged via merge queue, 21578e447).

```landing-facts
schema=landing-facts/1
plan_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
pr=#1609
merge_state=merged
cleanup_owed=false
deliverables_total=9
deliverables_done=9
total_tokens=10534182
total_wall_seconds=70372.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.pre-submission-self-review.may_close=no
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- Pre-submission self-review did NOT converge: 4 rounds (10/2/6/6 findings, 21 of 24 contract_drift); the operator closed it out of budget with the last 6 fixes (b473f1f7a) unreviewed by self-review.
- After the PR-review fix round (TASK-14..17, e568c3470..89fd46124) the operator chose "gates + push only": lessons-housekeeping, simplify, plugin-doctor and self-review were NOT re-fired against those fixes (their records stay anchored at 3a8bed617). Full verify (27761 tests), CI and CodeRabbit re-review covered them.
- Post-merge follow-up owed: run `orchestrator migrate-layout` over every epic ledger (request: orchestrator-refactor inbox ledger-decomposition-and-row-vocabulary-001); letter-suffixed ids like PLAN-PR-025B are refused as unmigratable_rows and need operator decisions.
- D2 prose reconciliation for review-apparatus/epic.md was routed to the review-apparatus inbox (ledger-decomposition-and-row-vocabulary-001), not edited.
- The chore(quality-gate) commit carries a ruff import-order fix to test/test_shared_harness_parse_ns_{defaults,no_seam}.py from main #1593 (outside plan scope).
- The manage-status transition mailbox probe reported not_orchestrated for this orchestrated plan at every phase transition (lesson 2026-09-23-15-001).
- marshalld reconcile deferred (daemon busy, owed x1).
