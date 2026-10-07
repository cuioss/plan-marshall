envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:51:01Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=A review bot reporting completed=true over a rate-limit refusal comment yields a green automated-review that saw no diff

# A bot's completion state is not evidence that the bot reviewed the diff

## Observation

On PR #1043 (plan `exploration-share-is-unmeasured`), automated review coverage was **1-of-3**:

- CodeRabbit: rate-limited. Reported `completed: true` **over a refusal comment**.
- Sourcery: rate-limited.
- pr-agent: reviewed.

The finalize pipeline read the completion state and moved on. Operator-accepted.

A completion signal was emitted with full confidence while the underlying work did not happen — the epic theme, at the review gate.

## Rule

- **A bot's completion/check state is not evidence of participation.** The only evidence is the bot's actual comments: `ci pr comments --pr-number N`.
- A refusal comment (rate limit, quota, "review skipped") accompanied by `completed: true` is a **detected refusal reported as a clean review**. The completion state must be reconciled against the comment body, and a refusal must degrade the reported coverage rather than pass through.
- `automated-review` should report **coverage as a fraction** (`reviewed_bots / enabled_bots`) with the refusing bots named, so a 1-of-3 run is visibly 1-of-3 and not simply green.
- Never read a green finalize as proof the bots saw the diff.

## Recurrence

This class has been observed before (a *detected* refusal reported as a clean review). Recording another instance so the recurrence count is not lost.
