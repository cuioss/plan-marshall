envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:31Z

# Candidate lesson: Sourcery review-budget refusal notice not recognised

Component: plan-marshall:automatic-review (refusal_patterns)
Category (proposed): bug
Source: plan code-analysis-base, finalize automatic-review (PR #31)

## Observation

Sourcery posted its review-budget refusal notice (it declined to review the PR) instead of a review. The automatic-review step reported `count_skipped_refusal: 0`: none of the configured `refusal_patterns` matched the notice, so the bot's non-review was not classified as a refusal and its completion state was misread.

## Proposed correction

Add a refusal pattern for the current Sourcery review-budget/limit notice wording, with a fixture taken from the real comment body, and make an unmatched bot comment that carries no findings surface as "unclassified" rather than counting as a completed review.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-002.md` from plan code-analysis-base (PLAN-36, #31)
