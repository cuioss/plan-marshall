envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:45:13Z

# Candidate lesson: distinguishing two states is only worth it if both remedies are reachable

**Source record:** `pr-comment` finding `dadd8a`, resolution `fixed`, CodeRabbit inline (Major, "heavy lift") at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:665`, reviewed commit `56580bd9d`. Remediated by TASK-10 in `851e5396b`.

## The observation

The paragraph at `SKILL.md:665` names two blocking members whose remedy is something other than waiting. Only one of them was actionable as written:

- `participated_stale` → pointed at the `re_review_on_loopback` path: a concrete, documented mechanism.
- `not_triggered` → the prose "generate the trigger event at all". **No invocation. No outcome recording. No timeout branch.**

So the document told the reader that awaiting a `not_triggered` bot is waiting for something that will never arrive, and then supplied no alternative to awaiting.

## Why it lands on the plan's own thesis

The plan's justification for splitting `not_triggered` out of `absent` is that the two states have **opposite remedies** — `absent` escalates, `not_triggered` needs the trigger generated. That justification is only redeemed if the remedy is reachable. A taxonomy member whose remedy exists solely as prose buys the reader a more precise diagnosis and no more capability than the conflated state it replaced. Worse than neutral, in fact: the reader is now told that waiting is futile, which removes the only action the old conflation left available.

The fix documented the concrete `github_re_review re-review` invocation per participating bot and recorded both the `matched` and `timed_out` outcomes, reusing the existing `re_review_on_timeout` policy from triggers A and B rather than defining a new one — which is the right instinct: the remedy already existed for a sibling state and needed wiring, not invention.

## The generalisable shape

**When a plan splits one state into N, the deliverable is N remedies, not N names.** A useful review of such a change asks, for each new member: what is the verb, what records its outcome, and what happens when it does not complete. Any member that answers those in prose only has not been shipped.

The transferable check is cheap: grep the new members' remedy prose for an actual invocation. A remedy sentence containing no command, no script notation and no outcome field is a name pretending to be a mechanism.

## Why it is routed here

This is the epic's own taxonomy and its own remediation flows. It also generalises to any state-splitting change, which is the orchestrator's call to make.
