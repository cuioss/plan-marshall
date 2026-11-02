envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=candidate-lesson
created=2026-10-20T20:29:22Z

# Candidate lesson: post-merge ci checks wait --pr-number errors once a merge-queue merge auto-deletes the head branch (plan-marshall:tools-integration-ci / phase-6-finalize branch-cleanup)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492, merge 03cb4755), lessons-capture step.

Related (not a recurrence): pending api-sheriff-api-sheriff-0-2-0 message "post-merge `ci checks wait --adaptive` ran into its deadline ..." — same post-merge wait surface, different failure.

## Observation

Work log 2026-10-20T20:26:23Z: branch-cleanup ran `ci checks wait --pr-number 492` after the merge queue merged the PR. The merge queue had already auto-deleted the head branch, and the wait returned `status: error`. The run continued only because the operator read main CI for merge commit 03cb4755 directly.

## Why it matters

Head-branch auto-delete is the normal end state of a merge-queue merge, so a post-merge wait keyed on the PR's head ref fails by construction in every repo using a merge queue. The error is indistinguishable from a real CI failure without manual inspection.

## Suggested direction

After a merge, resolve checks by the merge commit SHA (or the PR's recorded head SHA) instead of the head ref, or return a dedicated `head_ref_deleted` outcome naming the merge-commit lookup. The post-merge workflow step should use that path for merge-queue repos.
