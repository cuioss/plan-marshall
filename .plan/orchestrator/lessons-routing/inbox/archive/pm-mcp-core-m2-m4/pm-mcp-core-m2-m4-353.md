envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:51Z

# Sourcery review-budget refusal not recognised; filed as an ordinary pr-comment finding

**Component:** plan-marshall:automatic-review (Sourcery registry `refusal_patterns` in `automatic-review/standards/`), plan-marshall:workflow-integration-github `fetch_findings`
**Category:** bug
**Source plan:** plan-14-operator-and-question-stores (PR #93), from plan-retrospective

## Observation

Sourcery commented: "this account has used its review budget of 2,500,000 diff characters for the last 7 days. You can request another review in 10 hours by commenting `@sourcery-ai review`." The producer reported `count_skipped_refusal: 0`, with `refused_bots`, `unrecognised_refusal` and `refusal_pattern_drift` all empty. It filed the comment as pending finding `c51508`, and the unified triage had to dispose of it by hand (`accepted`). Sourcery is optional, so nothing was blocked, but the refusal-drift detector did not fire either.

## Suggested corrective action

- Add the "used its review budget of ... diff characters" wording (with its "request another review in N hours" ETA) to Sourcery's `refusal_patterns`, as a quota refusal with an awaitable window.
- Look into why `refusal_pattern_drift` stayed empty for a bot comment that has refusal shape but no code content. The drift detector is meant to catch exactly this case.
