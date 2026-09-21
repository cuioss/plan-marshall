envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T19:00:15Z

component=plan-marshall:automatic-review
category=bug

# Two review-bot registries disagree with what the run observed, and each disagreement changes a count

The bot registries are the authority the counting stages read. On this PR, two of the three enabled
bots behaved differently from their registry data blocks, and in both cases the divergence propagates
into a published number.

## Disagreement 1 — Sourcery: two refusal modes, only one in the store

`sourcery-ai`'s single record is **not a review**. It is a budget-refusal notice. The
review-retrospective records both sources and refuses to pick between them:

- The **run context** classifies the refusal as `cause=size, cap=150000 diff characters` against 3202
  changed lines — the per-PR ceiling shape (`refusal_size_patterns`, remedy: smaller diff).
- The **notice actually in the findings store** is the weekly account-quota shape (250,000 diff
  characters over 7 days, reopening in 5 days 4 hours — remedy: backoff).

These are the two refusal modes the registry deliberately separates, and they lead to different
remedies. Only one of the two reported refusals reached the store.

Consequence: Sourcery declares no `review_body_summary_patterns`, whose fail-closed default is
*counted*, so the refusal is scored as one **actionable** `review_body` and its `0.0%`
resolved-as-fixed is arithmetic over a notice. As the artifact states: *"`0.0%` here must not be read
as 'Sourcery was wrong about everything' — Sourcery produced no review content on this PR at all."*

## Disagreement 2 — PR-Agent: registry publish shape is the opposite of the observed one

> The PR-Agent registry doc states this bot posts no inline comments at all — exactly one persistent
> `issue_comment` headed `## PR Reviewer Guide 🔍`. This run recorded the opposite shape: one
> `kind=inline` record and zero `issue_comment` records for `cuioss-review-bot`.

The artifact draws the consequence explicitly: *"a counting stage that assumed the documented shape
would have concluded this bot found nothing."*

## Rule

Both are the same failure: a registry claim that the pipeline treats as fact, with no check that the
observation matches it.

1. **Add a refusal-mode discriminator to the stored record.** A refusal must carry which mode it is
   (`size` vs `weekly_quota`), because the remedy differs and the run context and the store currently
   disagree with no way to tell which is right.
2. **A refusal is not an actionable review_body.** Fail-closed *counted* is the right default for an
   unclassified body, but a recognised refusal notice must be excluded from `actionable_count` so
   `resolved-as-fixed` is not computed over it.
3. **Reconcile `publish_shape` against observation and report the divergence.** The registry's
   declared kinds and the observed kinds are both already in hand at counting time; a mismatch should
   be a reported finding, not a silent premise.
