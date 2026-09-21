envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:18:41Z

component=plan-marshall:automatic-review
category=bug
title=Gate bot-completion on the producer's terminal marker, never on absence of in-progress markers

# Gate bot-completion on the producer's terminal marker, never on absence of in-progress markers

## Context

The pre-merge review barrier armed four successive monitor predicates against
CodeRabbit on PR #1074. Three fired on non-events:

1. **Count-based** — `count_stored: 2` resolved to the plan orchestrator's *own*
   re-review request comment (`5309b5`) plus CodeRabbit's acknowledgment
   (`66fdb7`) whose body is "I will review the rebased pull request". A
   self-authored comment is not participation and an acknowledgment is not a
   review.
2. **Exclusion-list v1** — excluded the rate-limit notice and the I-will-review
   ack; fired on the third state, "review in progress, please wait".
3. **Exclusion-list v2** — extended the list again; still one state behind.
4. **Terminal-marker** — gated on the literal `Actionable comments posted:`,
   which only the completed walkthrough carries. Fired correctly, first time,
   with `CODERABBIT_REVIEW_COMPLETE: Actionable comments posted: 6`.

The run's own decision log states the generalisation at 19:47:46Z:

> Generalizable rule: gate on the terminal marker a producer emits when DONE,
> never on the absence of the in-progress markers you happen to know about,
> because the in-progress vocabulary is open-ended and the exclusion list is
> always one state behind.

That rule was recorded but never filed as a lesson — lessons-capture ran at
19:10, 37 minutes before the entry existed.

## Root cause

CodeRabbit publishes **at least four** distinct non-review states into the same
edit-in-place comment slot: rate-limit notice, I-will-review acknowledgment,
review-in-progress please-wait, and the completed walkthrough. A predicate built
as "not any of the in-progress states I know about" is defined over an open set.
Every new state the producer adds silently converts the predicate into a false
positive, and the failure mode is the worst kind — it reports *completion*.

The positive terminal marker is defined over a closed set of one: the producer
emits it exactly when it is done.

## Proposed action

1. Make the terminal-marker form the documented contract in `automatic-review`
   for every bot in the roster — each bot's entry names the literal string it
   emits on completion, not the strings it emits while working.
2. Explicitly prohibit exclusion-list predicates for completion detection in the
   barrier's standard; an exclusion list over a producer's in-progress vocabulary
   is a structural defect, not a tuning problem.
3. Add the self-authored-comment guard: the barrier must never count a comment
   authored by the plan orchestrator itself as participation. Note the related
   defect recorded at 19:45:48Z — self-response suppression is *inconsistent
   across fetches* in the same run (an earlier fetch reported
   `count_skipped_self_response: 1`, a later one ingested `5309b5` as a
   `pr-comment` finding).

## Evidence

- aspect: chat_history_analysis — five Monitor arms recovered from the session
  transcript; three of the five carry predicates that fired on non-events.
- decision.log `77e24a` (19:45:48Z) — "Monitor predicate was too weak and fired
  on a non-review… a self-authored comment is not participation."
- decision.log `118242` (19:47:46Z) — "Third weak monitor predicate… four
  distinct non-review states… gate on the terminal marker."
- transcript event `bk6aczifc` — `CODERABBIT_REVIEW_COMPLETE: Actionable comments
  posted: 6`, the predicate that worked.
