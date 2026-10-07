envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:44:42Z

# Findings filed during finalize die with the plan directory — there is no carry-out route

component: plan-marshall:manage-findings
category: improvement
confidence: high

## Context

This plan finished with eight PENDING findings in its plan-scoped store, filed across the run against components owned by five different skills. None is about the plan's subject matter; all are about the machinery the plan ran on.

- **c8e4a9** (error, manage-build-server) — a `timeout` verdict kills the daemon job but orphans the whole pytest process tree. Observed live: ten xdist workers survived the master kill and had to be signalled individually.
- **1f0c43** (manage-architecture) — a cold `architecture` crawl costs ~18s and several `run_script` subprocess budgets across the suite are sized as if script startup were cheap.
- **d4501c** (phase-6-finalize) — `review_commitments reconcile` returns `verdict: clear` over `commitments_considered: 0`.
- **5a5761** (manage-references) — `affected_files` under-records loop-back fix work, so every `affected_files`-derived finalize step under-scopes on any plan whose scope moved during execute.
- **18f362** (tools-integration-ci) — the CI payload cannot establish WHICH commit a run verified; run `head_sha` and run age contradict each other.
- **1d5140** (phase-6-finalize) — `ci_verify run` reports `persisted=false` / `persist_skipped_reason=head_sha` while it DID persist `head_at_completion`.
- **e8bde7** (workflow-integration-github) — `head_sha_verified` can never be true for pr-agent, whose re-review is an in-place comment edit, so the `participated_stale` remedy the barrier prescribes is structurally unreachable for it.
- **79a483** (insight, phase-6-finalize) — two ADR proposals that `adr-propose` could not create, because its Step 5 requires an `AskUserQuestion` and a dispatched leaf cannot reach the operator.

All eight live under `.plan/local/plans/{plan_id}/artifacts/findings`, which is removed when the plan directory is removed.

## Root cause

`lessons-capture` routes candidate-lessons to the epic inbox, and `delete-plan` carries lessons back with a veto when a carried lesson did not land. Neither has a findings equivalent. A finding filed at finalize has exactly one destination — a store scoped to the plan that is about to be deleted — and no route to the epic that owns the component it names.

This is adjacent to the footprint-resolver candidate already in this inbox (message 002): both are cases where finalize-ordered evidence outlives its own store's lifetime by zero, because the step that destroys the store runs before or beside the step that produces the evidence.

Note also that e8bde7 is squarely this epic's own subject matter — pr-agent participation verification — and would have been lost.

## Proposed action

Give `manage-findings` a carry-out at plan close: route every still-pending finding to the epic inbox as a message at `delete-plan`, the way lessons are carried back, keyed on the finding's recorded `component` so the receiving epic is derived rather than guessed. Apply the same veto shape `delete-plan` already applies to lessons — refuse the deletion when a carried finding did not land.

Until that exists, an orchestrated run should treat the pending-findings list as part of its landing payload. The eight above are named here so the orchestrator can act on them before the plan directory goes: five (5a5761, 18f362, 79a483, 1d5140, e8bde7) were filed during this finalize run and three (c8e4a9, 1f0c43, d4501c) earlier.

## Evidence

- `manage-findings list --plan-id review-packs-become-published-artifacts --resolution pending`: `filtered_count: 8` of `total_count: 24`
- `store_path: .plan/local/plans/review-packs-become-published-artifacts/artifacts/findings`
- The plan's worktree was already removed by `branch-cleanup` before this step ran; the plan directory is next
- No verb on `manage-findings`, `manage-status delete-plan`, or `plan-orchestrator inbox` routes a finding to an epic
