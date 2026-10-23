envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:33Z

component=plan-marshall:automatic-review
category=improvement
source=dispatcher-observed fact (3); work log 7702cf (2026-10-18T07:58:12Z)

# Sourcery's review-budget refusal forces an operator question on every head

## Observation

On re-review (trigger B) of head d3d46f2, sourcery returned a comment that does not reference the head SHA (a review-budget refusal). It was recorded as declined, not as a completed review. Every subsequent head then required an operator question to proceed without the sourcery review.

## Rule

A bot's budget or rate refusal is a known, classifiable state. Record it once per PR (or per rate window, through the manage-locks review-bot rate-window claim) as `declined: budget`, and let later heads inherit that disposition without asking the operator again, unless the window has reset.
