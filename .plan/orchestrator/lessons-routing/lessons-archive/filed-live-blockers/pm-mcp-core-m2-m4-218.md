envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:05Z

# Candidate lesson: Sourcery's review-budget notice is not recognised as a refusal pattern

Source: PR #50 pr-comment findings ad35df and 2760d7 (both accepted manually) plus dispatcher note

## What happened

Sourcery posted "Sorry @..., this account has used its review budget of 2,500,000 diff characters for the last
7 days. You can request another review in N days ..." twice on PR #50. The automatic-review pipeline did not
recognise it as a bot refusal / quota notice; it surfaced as a decline/pending finding each time and had to be
dispositioned by hand.

## Candidate rule

Add the Sourcery "used its review budget of N diff characters" wording to the review-bot refusal patterns so the
bot's completion state reads as declined (quota) automatically and no pending pr-comment finding is filed.

Likely owner: plan-marshall:automatic-review / plan-marshall:workflow-integration-github (bot_completion refusal
patterns).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-009.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
