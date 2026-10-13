envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:47Z

# Sourcery review-budget refusal is not recognised as a refusal (refusal_patterns drift)

## What happened

On PR #49 (pm-mcp-core) sourcery-ai answered both review rounds with:

> Sorry @cuioss-oliver, this account has used its review budget of 2,500,000 diff characters for the last 7 days.
> You can request another review in 3 days and 6 hours by commenting `@sourcery-ai review`.

The plan-marshall producer did not match this wording against the bot's refusal_patterns, so each reply was filed as an ordinary pending `pr-comment` finding (1b252d, 99808d) instead of being classified as a review refusal. It surfaced twice as pending review work and had to be closed by hand as `accepted`.

## Rule / fix direction

The sourcery refusal_patterns must cover the review-budget wording ("used its review budget of ... diff characters for the last 7 days"). More generally, a bot's refusal / quota notice is a state of the bot, not a review comment: the producer should classify it as a refusal (no review delivered) and not file it as a pending finding. Add the current wording to the patterns and a fixture test with the verbatim text above.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-002.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
