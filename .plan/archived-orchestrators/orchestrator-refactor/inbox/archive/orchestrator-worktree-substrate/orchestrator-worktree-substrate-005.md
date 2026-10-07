envelope_version=1
sender_type=plan
sender_id=orchestrator-worktree-substrate
epic=orchestrator-refactor
kind=landing
created=2026-09-28T19:18:39Z

## What landed

orchestrator-worktree-substrate shipped as #1652 (merged via the platform merge queue, squash 438a0a71f).

```landing-facts
schema=landing-facts/1
plan_id=orchestrator-worktree-substrate
epic=orchestrator-refactor
pr=#1652
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=12966861
total_wall_seconds=104820.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.create-pr.pr_number=1652
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

- pre-submission-self-review was closed by operator override at HEAD 840657a after the loop-back ceiling (5/5) was exhausted: the full-surface round was clean (263 candidates, 0 findings) but the verifier refused the verdict (finding 5f65bb, accepted). The verifier's stated reason partly misread counts.total as 222 schema files + 41 contract sources; the valid half is that the author envelope had no Grep and did not read every contract source in full.
- Sourcery refused the PR on size (cap 150000 diff characters; measured 4010 changed lines) — optional bot, did not gate.
- `ci checks pull-request-runs` reported has_pull_request_run=false / run_count=0 for PR #1652 although pull_request CI checks exist on the PR — possible observable defect in the not_triggered read (review-apparatus).
- worktree-remove --plan-id _orchestrator is refused only incidentally by the move-back guard (plan_dir_not_moved_back), not by a dedicated reserved-key check like the new worktree-create guard.
- Simplify recorded an advisory near-identical-helper finding: base-branch resolution in _cmd_orchestrator._cutover_refusal duplicates orchestrator_worktree._default_base_branch().
- CodeRabbit walkthrough raised two inferred Medium security notes filtered as noise: an already-registered _orchestrator worktree is reused without verifying it is on the ledger branch; an unreadable main-checkout config silently falls back to the primary checkout.
- merge_commit_sha recorded as the landing commit 438a0a71f rather than main HEAD (c9c67839c, #1655 landed after the queue merge); branch-cleanup's "rev-parse HEAD" instruction is wrong whenever another PR lands before switch-and-pull.
