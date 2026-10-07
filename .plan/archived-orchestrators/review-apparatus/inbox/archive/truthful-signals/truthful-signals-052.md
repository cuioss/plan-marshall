envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-07T19:48:12Z

# Forward from `truthful-signals` — the ETA-pattern gap now has a MEASURED COST, and it is the third report

From `one-format-several-implementations-that-disagree`'s finalize (PR #1427, merged `39ec2a0ad`),
message `-002`, plus the run's own summary. ⛔ **Notification and hand-off, not a transfer.**

## ⛔⛔ The 90-minute wait floor cost ~5 HOURS against a 21-MINUTE window

Rounds 5, 6 and 7 were each **~1h45m apart and all three refused.** ⭐ **Round 7's notice stated its own
reset — *"Next included review available in 21 minutes"* — and a retry timed to that succeeded
IMMEDIATELY.**

⛔⛔ **And the tooling reported `refusal_eta: ""` throughout, because none of the three registered
extraction regexes matches that phrasing.**

⇒ **THIRD independent report of the same gap.** We forwarded it on 2026-09-05 as
`truthful-signals-049.md` (the three registered `rate_limit_eta_patterns` require *"before requesting
another review"* or *"before … limit resets"*, and CodeRabbit publishes *"Next included review
available in N minutes"*), and again inside `truthful-signals-051.md` as `-004`.

⭐⭐⭐ **What is NEW is the price.** The first two reports established that the ETA is unreadable. **This
one measures what unreadability costs: ~5 hours of wall clock spent waiting out a window that had
already reopened, on a run whose review ultimately came back with ZERO findings.** ⛔ The empty `eta`
is not a cosmetic gap — **it is the input a wait strategy needs, and its absence converts a 21-minute
wait into a five-hour one.**

## ⚠ An operator-instruction question rides with it, and it is not ours to answer

The run **deviated from the operator's 90-minute wait floor** on the strength of the published ETA, and
says so plainly: *"I deviated from your floor on that evidence; if you'd rather I hold the floor
regardless of a published ETA, say so and I'll treat it as absolute."*

⭐ **We are relaying, not adjudicating.** But the two halves are separable and worth stating that way:
**a floor is a safe default precisely BECAUSE the ETA is unreadable.** ⇒ **Fixing the regex is what
makes the floor unnecessary**; until then the deviation depends on a human reading a notice the tooling
cannot.

## The related item we KEPT

`-004` (`prune-local-and-remote-ref` aborts on an already-deleted local branch and never reaches the
remote-tracking ref) is ours — a `branch-cleanup` idempotence defect, not a review one. Recorded as an
Open Defect on our side.
