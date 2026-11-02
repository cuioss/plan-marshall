envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T09:32:38Z

# Candidate lesson: execute_commits_unrecorded miscounts after the finalize baseline rebase

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 001. Suggested route: plan-marshall (manage-status transition guard / phase-5-execute Step 10a / phase-6-finalize finalize-step-sync-baseline).



**Signal:** script-failure cluster (`plan-marshall:manage-status:manage-status`, exit 1, `failure_kind=script_internal_failure`).

## What happened

After the code-review loop-back (TASK-10), the 5-execute -> 6-finalize transition was refused at 2026-10-16T07:46:24Z:

> 7 of 8 worktree-branch commit(s) since diverging from main carry no kind=change ledger row. Run the phase-5-execute Step 10a settlement bookkeeping for the unrecorded commits, then retry the transition.

Work-log row 687bae lists `unrecorded_commits=818d88fb,f6adf36d,4e583539,647c3d88,95cdb965,238ead49,863e5fa5`, with `recorded_count=6`, `branch_commit_count=8`.

Two separate defects show up in that list:

1. **The base commit was counted as a branch commit.** `818d88fb` is the commit `main` was at (`main_sha=818d88fb...` in every execute re-entry). It is not plan work. The divergence point seems to have been computed against a stale local `main` (behind `origin/main`) instead of `origin/main`. As a result the guard treated the base as an unrecorded deliverable commit.
2. **The finalize rebase orphaned the ledger rows.** `finalize-step-sync-baseline` rebased the branch at 06:24:47Z, which rewrote every deliverable SHA (86b5564d, 61a855e7, 0cab9698, 5867df45, a176651d and the security-audit commit). The `kind=change` rows recorded during execute still name the pre-rebase SHAs, so none of them match any more. The orchestrator had to re-record the settlement rows by hand before the transition went through.

## Suggested corrective action

- Compute the branch-commit set against `origin/{base}` (or the recorded `main_sha`), never against the local base ref.
- Either have the baseline rebase re-key `kind=change` rows (old SHA to new SHA by patch-id), or have the guard match on patch-id or tree content rather than on the literal SHA.
