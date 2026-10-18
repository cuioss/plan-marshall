envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:40Z

# Candidate lesson: Add Sourcery's review-budget notice to its refusal_patterns

Source: plan-retrospective (chat-history-analysis + automatic-review returns), plan-69-unit-frontmatter-and-types
Component (suggested): plan-marshall:automatic-review (foreign bundle - route to plan-marshall lessons inbox)
Category (suggested): bug

## Context

On PR #91 the optional bot `sourcery` answered both review passes with a budget notice ("has used its review budget of 2,500,000 diff characters for the last 7 days ... another review is possible in about 16h27m via @sourcery-ai review"). Both times the producer left `refused_bots[]` and `unrecognised_refusal[]` empty and filed the notice as an ordinary `pr-comment` finding (1b0d2c, then bd358a), which triage then had to recognise by hand and accept.

## Root cause

The sourcery entry in the review-bot registry (`automatic-review/standards/sourcery.md` `refusal_patterns`) does not match the review-budget wording, so the refusal is classified as code feedback.

## Proposed action

Add a refusal pattern for the review-budget notice (cause `quota`) to the sourcery registry entry, so it lands in `refused_bots[]` with a retry-after hint and never becomes a triage finding.

## Evidence

- automatic-review pass 1: "Possible registry gap ... refusal_patterns ... may need this wording" (finding 1b0d2c)
- automatic-review pass 2: same notice stored again as bd358a; triage accepted both as non-code feedback
