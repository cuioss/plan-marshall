envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T20:35:27Z

# Candidate lesson: Sourcery review-budget refusal not matched by refusal_patterns

**Component (suggested):** plan-marshall:automatic-review
**Category (suggested):** bug

## Observation

On PR #56 the Sourcery bot refused to review with a review-budget message ("2,500,000 diff characters for the
last 7 days"). The configured `refusal_patterns` did not recognise it, so the refusal was filed as an ordinary
pr-comment finding instead of being classified as a bot refusal (no review performed).

## Root cause

The refusal pattern set for Sourcery does not cover the weekly diff-character budget wording.

## Suggested correction

Add a pattern for the Sourcery budget refusal (match on the stable part, e.g. "diff characters for the last"
and "days") to the Sourcery refusal_patterns, with a fixture test of the verbatim message, so the bot is
reported as refused/not-reviewed rather than producing a pr-comment to triage.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-17-project-units-and-invariants-003.md` from plan plan-17-project-units-and-invariants (PLAN-17, #56; harness Claude Code)
