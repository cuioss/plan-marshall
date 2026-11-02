envelope_version=1
sender_type=plan
sender_id=plan-v02-46-upstream-close-after-early-answer
epic=lessons-routing
kind=finding
created=2026-10-22T18:04:12Z

# Recurrence: git-workflow commit reports FETCH_FAILURE when nothing is staged (plan-marshall:workflow-integration-git, phase-6-finalize item 7c(4a))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-46-upstream-close-after-early-answer (PR cuioss/API-Sheriff#513, merge e70743f), lessons-capture step.

Recurrence of plan-v02-12-idp-addressing-model-001 ("git-workflow commit does not stage files and reports a misleading FETCH_FAILURE when nothing is staged").

## Observation

The `workflow-integration-git` `commit` verb again returned `error_code: FETCH_FAILURE` with "git commit failed: exit 1" when the index was empty. This time the caller was the phase-6-finalize inline-review commit path (item 7c(4a)), which commits without staging first.

## Why it matters

Second plan in this epic to hit it. Besides the misleading error class, the finalize inline-review path itself is missing a stage step, so it fails every time an inline-review fix is committed through it.

## Suggested direction

Two fixes: (1) return a dedicated `nothing_staged` error before the commit call; (2) make phase-6-finalize item 7c(4a) stage the fix footprint (or call a verb that stages) before committing.
