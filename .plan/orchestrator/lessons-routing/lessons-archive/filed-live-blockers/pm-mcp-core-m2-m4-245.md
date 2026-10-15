envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:10Z

# Sourcery's 7-day review-budget notice is not recognized as a refusal

## What happened

On PR #53, sourcery-ai posted a comment saying it would not review the PR:

> Sorry @cuioss-oliver, this account has used its review budget of 2,500,000 diff characters for the last 7 days. You can request another review in 2 days and 9 hours by commenting `@sourcery-ai review`.

None of the `refusal_patterns` in the sourcery entry of the review-bot registry matched this text. The pipeline therefore filed it as an ordinary pr-comment finding (hash 7a5066), which then had to be triaged and resolved `accepted` by hand. It was not recognized as "this bot declined to review", so the bot's completion state and the wait logic treated it as if sourcery might still post a review.

## Rule / fix

- Add a refusal pattern to sourcery's registry entry for the budget-exhausted notice. The fixed part is "has used its review budget"; the number of characters and the remaining time change between notices, so they must not be part of the pattern.
- More generally, refusal patterns should cover quota and rate-limit notices from every registered bot, not only "PR too large" or "skipped" messages. A test fixture should hold the exact notice text from each bot.

## Evidence

pr-comment finding 7a5066 in plan-39-module-readmes-and-adrs (author sourcery-ai, kind issue_comment, resolved accepted).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-004.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
