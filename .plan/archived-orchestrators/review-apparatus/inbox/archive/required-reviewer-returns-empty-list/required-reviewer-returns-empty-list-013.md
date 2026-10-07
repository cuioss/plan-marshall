envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=landing
created=2026-09-05T16:48:44Z

## What landed

required-reviewer-returns-empty-list shipped as #1410 (merged).

```landing-facts
schema=landing-facts/1
plan_id=required-reviewer-returns-empty-list
epic=review-apparatus
pr=#1410
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=8628382
total_wall_seconds=103479.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.action=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.create-pr.pr_number=1410
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-preference-emitter.patterns_promoted=0
total_billing_weighted=142487850
loop_back_iteration=4
loop_back_max_iterations=17
```

## Residue

- **The finalize gate dominated the run.** 8.63M tokens total against a 3-file
  change; `6-finalize` alone accounted for 6.20M across 4 loop-back iterations
  and 32 dispatched step firings. Billing-weighted total is 142.5M. The run took
  28h44m wall / 6h31m worked / 22h13m idle. `loop_back_iteration` reached 4 of a
  ceiling of 17, so this run converged rather than exhausting its budget — unlike
  PLAN-TRUTH-089, which consumed all 17.

- **The plan's own subject component failed 5 times during its own finalize.**
  `plan-marshall:automatic-review:review_completeness check` — the gate that
  decides whether required reviewers participated — took 3 argparse rejections
  and 2 exit-1 internal errors. The exit-1 cause is now ESTABLISHED (it did not
  need reproducing, contrary to the retrospective's sibling message 002): both
  are deliberate `malformed_bot_flag` refusals — `--participated-bots
  cuioss-review-bot` passed a bare token where a `bot_kind:evidence_kind` pair is
  required, and `--refused-causes sourcery=quota` used `=` where `:` is the
  separator. Both fired at 15:19Z, 16 seconds after the merge lock went
  `lock-owned`. Filed as candidate-lesson 009.

- **Review coverage was narrower than the merge gate proves.** The
  `automatic-review` step's own detail records `1 reviewed, 1 empty, 1 refused`
  across the three configured bots. A merge that cleared the barrier is not
  evidence that three reviewers read this diff.

- **Stale worktree metadata blocked re-entry.** After `branch-cleanup` merged and
  removed the worktree, `metadata.use_worktree` stayed `true` and
  `metadata.worktree_path` still named the deleted directory, so every later
  phase-entry assertion refused with `worktree_unresolved` and the finalize could
  not be resumed until the metadata was hand-repaired with two `manage-status
  metadata --set` calls. This is the known `bd825d` defect (`worktree-remove` is
  not the symmetric counterpart of `worktree-create`, which sets both fields);
  this run is a second confirmed occurrence.

- **The post-run-review dirty-path guard attributes by observation, not
  authorship.** It reported `uv.lock` dirty against 5 consecutive post-merge
  steps, none of which wrote it. The file was already dirty at this run's
  `5-execute` handshake capture; the cause is dependabot PR #1417 raising the
  ruff specifier without refreshing the lock, so every local build re-resolves
  and dirties the tree. Recorded once as finding `5ac74f` with provenance rather
  than re-filed per step. Filed as candidate-lesson 010.

- **`manage-logging read --phase` appears not to filter.** Two reads with
  different `--phase` values returned the same `total_entries: 396`, and the
  shorter result was exactly the tail of the longer one. A declared filter that
  silently no-ops is a vacuous-filter defect. Observed during lessons-capture,
  outside that step's candidate population, so not emitted as a candidate-lesson.

- **Plugin registry pin inversion, still open.** `installed_plugins.json` pins
  all 10 bundles at `0.1.1592` while the executor resolves `0.1.1607` — 15
  versions behind, so in-process `Skill:` dispatches load stale bodies. Operator
  repair only; not caused by this plan.

- **Twelve candidate-lessons were routed to this epic**, not to the global
  corpus: 001–006 from `plan-retrospective`, 007–012 from `lessons-capture`.
  Message 008 states its 6-notation table as a floor, not a complete set: the
  dispatcher observed 8 distinct failing notations, and 2 lie outside the log
  window that step paged.
