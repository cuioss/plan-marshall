envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T09:57:51Z

# Candidate lesson: branch-cleanup switch-and-pull fails when the main checkout is on another branch with local edits (plan-marshall:phase-6-finalize)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-43-validator-reserved-header-topology-rules (PR cuioss/API-Sheriff#505), local lesson 2026-10-22-08-003.

## What happened

After PR #505 merged (1e53ab4f) and the plan worktree was removed, the `branch-cleanup` step ran `switch-and-pull` on the main checkout. The main checkout was not on `main`: another session had it on `fix/release-promote-tags-after-verify` with uncommitted changes to `.github/workflows/release.yml` and `doc/development/release-process.adoc`. `git checkout main` would have overwritten them, so the step failed with `pull_failed` (work log 6302f4, 08:51:17Z).

The step handled it safely: it left the checkout and the edits alone and still recorded `branch-cleanup` as done. But the failure was logged as `[ERROR]`, and the local `main` was not updated.

## Why it matters

With worktrees, the main checkout is shared with other sessions and with the operator. It is normal for it to be on another branch with work in progress when a plan finishes. Reporting this as an error suggests something broke, and a less careful implementation could try to stash or force the checkout and damage someone else's work.

## Suggested direction (for plan-marshall)

- Before `switch-and-pull`, check the main checkout's current branch and whether it has uncommitted changes. If it is on another branch or dirty, do not switch; update `main` with `git fetch origin main:main` instead (this works when `main` is not checked out), or skip the update.
- Report the skip as an informational outcome (for example `main_checkout_busy`), naming the branch, not as `[ERROR]`.
- Never stash, reset or force-checkout in the main checkout.

## Provenance

Observed in plan `plan-v02-43-validator-reserved-header-topology-rules`, epic `api-sheriff-0-2-0`, PR #505. The other session's branch and files were left untouched. Filed in the API-Sheriff store only because the plan-marshall `lessons-routing` inbox could not be written from the lessons-capture step. Route it to that inbox and remove this local copy afterwards.
