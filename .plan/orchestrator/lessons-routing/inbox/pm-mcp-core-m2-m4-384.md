envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:08Z

component=plan-marshall:automatic-review
category=improvement

# Optional review bot Sourcery answered only with a weekly review-budget refusal

Source: run observation reported by the orchestrator (automatic-review step on PR #107), plan plan-70-plan-instance-alignment.

The optional bot Sourcery posted nothing but a refusal saying its weekly review budget was used up. The step still waited for it and processed the refusal as its answer, which contributed no review.

## Rule / fix direction

automatic-review should recognise a bot's budget/quota refusal as "bot unavailable" (not as a completed review with zero findings), record it as such in the step outcome, and skip waiting on that optional bot for the rest of the window - in line with the cross-plan review-bot rate-window claim in manage-locks.
