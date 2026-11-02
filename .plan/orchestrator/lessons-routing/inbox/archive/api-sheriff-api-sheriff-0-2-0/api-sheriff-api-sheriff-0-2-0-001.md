envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T15:35:20Z

# Candidate lesson: Review-bot quota exhaustion burns loop-back rounds while nothing changes (plan-marshall:automatic-review)

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-28-validator-limit-rules` (PR cuioss/API-Sheriff#467), source message 001.


## What happened

CodeRabbit (a required reviewer) refused to review PR #467 for about six hours (06:57-12:44Z) because the org-shared free quota was exhausted. Every `@coderabbitai review` trigger posted inside that window only produced a "Review rate limited" reply. Each automatic-review re-fire still consumed a finalize loop-back round, so 3 of the 5 available rounds were spent while the PR and the review state stayed exactly the same. CodeRabbit finally reviewed after the third 90-minute wait.

## Lesson

A "Review rate limited" reply is a quota state, not a review outcome. It should not cost a loop-back round. When the automatic-review step sees a rate-limit reply from a required bot, it should:

- classify the outcome as a distinct `rate_limited` / waiting state rather than an outstanding-review loop-back,
- wait out the quota window (the observed reset needed several 90-minute waits) without spending the loop-back budget,
- re-trigger only once the window has plausibly reset, instead of posting more triggers that only produce more rate-limit replies.

## Impact

With 5 rounds total, a single quota outage can exhaust most of the budget and leave too few rounds for real review findings.
