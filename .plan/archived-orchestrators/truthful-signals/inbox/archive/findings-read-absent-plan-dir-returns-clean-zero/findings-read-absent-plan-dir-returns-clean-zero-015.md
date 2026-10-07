envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=landing
created=2026-08-30T14:20:23Z

## What landed

findings-read-absent-plan-dir-returns-clean-zero shipped as #1369 (merged) — an absent findings store is no longer reported as a clean zero, on any surface.

```landing-facts
schema=landing-facts/1
plan_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
pr=#1369
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=7075456
total_wall_seconds=96642
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.branch-cleanup.merge_state=merged
step.create-pr.pr_number=1369
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=3
merge_commit_sha=09f92b5e8efd3f0f1e4459188f2331bf5a66a5eb
total_billing_weighted=172865135
loop_back_iterations=3
```

## Residue

Items the epic should track that no step recorded as a fact. Fourteen candidate-lesson messages
(`-001` through `-014`) carry the detail; this section names only what is not already a fact above.

- **PR identity changed mid-run.** The plan opened #1367, which was CLOSED UNMERGED at operator
  direction after CodeRabbit bound a review run to it that sat "in progress" for ~9 hours and then
  rate-limited on re-trigger. #1369 carries the identical branch and commits and is what merged.
  Re-opening as a new PR recovered in full a review that a 17-minute wait and a ~9-hour wait both
  failed to recover — the refusal was bound to the PR, not to the diff or the budget. This disagrees
  with the remedy `rate_limit_class: awaitable_window` prescribes. One observation; not promoted to
  policy.

- **Scope grew twice after phase-3, both operator-directed.** Deliverable 3 (the freshness scope
  discriminator) was added during phase-5; the github/gitlab provider hardening was added during
  finalize. The plan's declared footprint never caught up — 19 declared against 44 realized — because
  `sync-affected-files` re-derives from the outline, which no longer describes what the plan touched.

- **A lesson was destroyed with no tombstone during this run.** `2026-08-27-16-001` was logged
  `retained` at 22:11:13Z and is now `not_found` with the corpus at 11 and no tombstone. This run
  cannot establish which operation removed it. It matches the 2026-08-27 `2026-08-25-05-001`
  destructive-remove instance, so n >= 2. Its content survives only in candidate-lesson `-004`/`-014`.

- **Five findings were routed to this epic in prose only.** `ff2174`, `814a5b`, `266d55`, `7bbc84`
  and `5c47c6` each carry "routes to the truthful-signals epic" in their `resolution_detail`, but a
  resolution naming a destination is not a transfer, and the plan-scoped findings store dies with the
  plan. Messages `-008` through `-012` are the actual delivery.

- **External review found what five internal passes did not.** `pre-submission-self-review` ran five
  passes, produced 11 findings, resolved all of them, and reported the diff clean. CodeRabbit then
  found 5 more on the same tree — between a quarter and a third of everything discovered, depending
  on whether a mis-classified run summary is counted. One of the five was a `RuntimeError` escaping a
  guard whose function documented a `(None, reason)` contract; another was a negative control that
  could not fail for the reason it was written to guard, and that control had been written one commit
  earlier to prove the first finding fixed.
