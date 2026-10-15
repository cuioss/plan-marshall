envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:56Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-006.md 
> RECURRENCE of lessons-routing inbox messages already routed by this epic: pm-mcp-core-m2-m4-204, -218, -231, -235, -245, -254 (queued). Fold into those; this is new evidence from another plan, not a new lesson.

# Candidate lesson: Sourcery review-budget refusal is not a registered refusal pattern

Plan: static-verifier-residuals (PR plan-marshall/pm-mcp-core#66).
Signal source: automatic-review step (signal_automated_review_count = 1).

## What happened

Sourcery answered the PR with a refusal stating it had used its review budget. That text is
not in Sourcery's `refusal_patterns` registry, so the automatic-review pipeline could not
classify the comment as a bot refusal (no review performed) and it surfaced as an outstanding
review item instead of a recognised "bot declined" completion state.

## Candidate rule

Add the Sourcery review-budget refusal wording to the provider's `refusal_patterns` registry
(workflow-integration-github / automatic-review bot configuration), so a budget refusal is
recorded as a bot that did not review rather than as an actionable comment or a missing review.

## Suggested owner

plan-marshall automatic-review / workflow-integration-github (review-bot refusal registry).
Classification deferred to the orchestrator.
