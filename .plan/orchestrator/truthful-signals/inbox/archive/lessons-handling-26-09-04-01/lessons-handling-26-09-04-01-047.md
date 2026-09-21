envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:34:23Z

component=plan-marshall:automatic-review
category=bug

Relayed from Token-Sheriff PLAN-08 (PR #730 / `c40963ac`). ⚠ Observed end-to-end: the barrier blocked **correctly** (a required bot had not seen the correction commit), but the built-in self-healing path was disabled in this project, so the only way through was a hand-requested review — which returned in **69 seconds**. ⛔ A barrier whose only recovery is manual is a barrier that will be forced rather than satisfied.

# Candidate lesson: pre-merge review barrier was unclearable by loop-back because `re_review_on_loopback` is false

**Origin signal**: run observation offered by the orchestrator for judgement (not one of the three counted signals).
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).

## Observation

The pre-merge review barrier blocked the merge. The cause: the required bot
`cuioss-review-bot` had reviewed only the **pre-fix HEAD**. After the in-run fixes
advanced HEAD, the bot's approval no longer covered the tree being merged, so the
barrier correctly refused.

The important part is the shape of the deadlock: `re_review_on_loopback` is **false**,
so a loop-back could not have cleared it. The barrier's stated remedy (loop back, get
re-reviewed) was structurally unavailable under this configuration. What resolved it was
an explicit `github_re_review` trigger, which cleared in **69 seconds**.

## Why it is candidate-lesson shaped

This is a gate whose blocking condition is real and whose advertised escape hatch is
disabled by configuration. An agent that trusts the barrier's remedy will loop back,
observe no change in the barrier state, and loop again — the identical-repeated-failure
signature — while the actual fix is a different action entirely, and a fast one.

Possible correctives (for the orchestrator to judge):
1. When the review barrier blocks on an unproven bot, the remedy to reach for is an
   explicit re-review trigger, NOT a loop-back — and specifically so whenever
   `re_review_on_loopback` is false, where loop-back cannot clear the barrier by
   construction.
2. Better: the barrier's own refusal payload should name which remedy is available under
   the live configuration, rather than naming a remedy the configuration has disabled.
   A gate that suggests an unavailable fix invites a retry loop.

The 69-second resolution time is worth carrying: the correct action is cheap, so the cost
of this defect is entirely in the time spent attempting the wrong one.

## Cross-plan judgement deferred

Whether this is a lesson about the barrier's messaging, a lesson about the
loop-back-vs-re-review decision, or a project configuration question about
`re_review_on_loopback` itself is the orchestrator's call. This plan transmits the
candidate only.
