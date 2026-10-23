envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:06Z

component=plan-marshall:phase-6-finalize
category=improvement

# Residual for the plan PR body re-raised at the new head after operator acceptance

Source: Q-Gate 6-finalize finding 328ad4 (functional-review, residual at D10.R1 at the new head; resolved in run as accepted), plan plan-70-plan-instance-alignment.

After commit 8c36987, the residual reappeared as "this plan PR body must name plan-marshall-documentation PR 96 (merged) and list the roadmap and PM-IMPL-5 documentation parts as Owed to the milestone exit; it is written after this review". It is the recurrence of ea6e2e: an obligation on an artifact finalize writes after the review, re-raised because the head moved.

## Rule

Obligations on the PR body (naming a foreign PR, listing Owed items) belong to the PR-creation step as checklist input, not to the functional review's residuals. Same cluster as 22e83d / 82db0b / ea6e2e / d90ef8 - the orchestrator may merge these five into one lesson.
