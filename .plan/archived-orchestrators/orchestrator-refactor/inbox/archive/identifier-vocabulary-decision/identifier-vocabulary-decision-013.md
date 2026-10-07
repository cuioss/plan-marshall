envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=landing
created=2026-09-20T08:34:47Z

## What landed

identifier-vocabulary-decision shipped as #1543 (merged).

```landing-facts
schema=landing-facts/1
plan_id=identifier-vocabulary-decision
epic=orchestrator-refactor
pr=#1543
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=17375009
total_wall_seconds=68029.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,finalize-step-simplify:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,architecture-refresh:done,pre-push-quality-gate:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
```

## Residue

- `emit-landing` was never composed into this plan's manifest at outline time: `request.md` carried `source: description` with no recorded `source_id` (a phase-1-init gap — the file-pointer branch's `--source-id` was omitted at init), so the compose-time orchestration detector classified this plan as non-orchestrated and dropped both `emit-landing` and the `plan-marshall:plan-retrospective`/`lessons-capture` orchestration routing from the manifest snapshot. Both were corrected at finalize time by resolving `orchestrator inbox detect` directly against the known originating spec path (`.plan/local/orchestrator/orchestrator-refactor/plans/PLAN-04-identifier-vocabulary-decision.md`) and this landing message is the manual discharge of the step that gap dropped. Future orchestrator hand-offs should verify phase-1-init actually records `source_id` on the file-pointer branch — this is a real, reproducible init-time defect, not specific to this plan.
- A forked finalize subagent could not complete `branch-cleanup`: its Bash cwd was pinned to the worktree with no persisting `cd` across calls, so `worktree-remove` and the nine steps after it were unreachable from that fork. The parent session cd'd to the main checkout directly and completed the remaining pipeline itself. Forking across the `worktree-remove` boundary should be treated as structurally unsupported.
- D4's PLAN-05 execution brief was independently verified as transferred: it is present in this epic's inbox, filed as `kind: finding` because the inbox's closed kind enum (`landing`/`finding`/`candidate-lesson`) has no dedicated member for an execution brief.
- `references.json`'s `realized_footprint` records `uv.lock` as part of this plan's realized changes, but the merge commit (`4804b6976`) does not contain it — an unrelated dependabot re-lock (#1541) landed the same content first, and this plan's own `uv.lock` commit collapsed to a no-op during the pre-merge rebase. The operator's "absorb into this PR" intent was satisfied by #1541, not by this plan's own commit.
