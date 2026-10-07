envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:50Z

component=plan-marshall:manage-architecture
category=anti-pattern
title=The adaptive-timeout learner ratchets monotonically with no contention discount

# The adaptive-timeout learner ratchets, and one noisy run re-tiers a step permanently

## What was measured

Across the single plan `mandatory-plan-id-build-results-ledger`, the live-resolved
`bash_timeout_seconds` for `module-tests plan-marshall` moved in one direction only:

| Time | `bash_timeout_seconds` | Tier | Recorded at |
|---|---|---|---|
| compose time | 542 | `per_task` | decision log, 17:48:14Z retrospectively |
| 14:25:43Z | 836 | orchestrator | yield 1 |
| 14:59:33Z | 622 | orchestrator | yield 2 |
| 15:57:25Z | 692 | orchestrator | yield 3 |
| 16:57:31Z | 763 | orchestrator | yield 4 |
| 17:48:14Z | **1013** | orchestrator | yield 5 |

The 17:48:14Z decision entry names the cause explicitly:

> Live tier re-resolve for module-tests plan-marshall now returns
> `execution_tier=orchestrator`, `bash_timeout_seconds=1013`. The compose-time and earlier live
> values were `per_task` at 542s. **The learned duration rose after the contended 474s run**, so
> the step has left the leaf runnable slice.

And the run that caused it was independently diagnosed as contention, not change:

> wrapper reported `status=timeout exit_code=-1` at the 457s learned budget, but the pytest log
> ran to completion GREEN — 14212 passed, 2 skipped in 474.64s, zero failures. **Cause is host
> contention (the identical suite took 174.48s minutes earlier), not the change.**

174.48s → 474.64s for the *identical suite* is a 2.7× contention factor. The learner absorbed
the 474s observation at full weight.

## The consequence

Once `bash_timeout_seconds` crosses the 600s harness ceiling, `exceeds_bash_ceiling=true` and
the step permanently leaves the leaf's runnable slice. For the remainder of this plan **no
`module-tests` gate could run `per_task` again**, forcing **6 orchestrator-tier yields**, each
costing an envelope round-trip: the leaf yields, the orchestrator runs the build through
`await-long-running`, the orchestrator re-dispatches. Three of the nine phase-5 dispatch
boundaries are directly attributable to this.

The leaf behaved **correctly** at every one of those yields — it refused to run or background an
orchestrator-tier step and recorded the tier decision with its evidence. The cost is structural,
not a discipline failure.

## The defect

The learner has **no contention discount and no downward path within a run**. A single
noisy-neighbour execution permanently re-tiers a step for the rest of the plan, and the very
run that caused the ratchet was one the agent had *already diagnosed in writing* as contention
rather than a real duration change. The diagnosis existed; the learner could not consume it.

## Do this instead

- **Discount an observation the wrapper itself flagged as `timeout` while the inner log
  reported a clean completion.** That combination is the signature of contention (the
  inverse-polarity outer-status case, already a known archetype here), and it is exactly the
  observation that should carry *less* weight, not full weight.
- **Use a robust statistic** (trimmed mean, median, or a high percentile over a window) rather
  than letting one sample ratchet the budget. 174s and 474s in the same session for the same
  suite should not produce a 1013s budget.
- **Allow the budget to fall.** Monotone-increasing is a safe default only if the cost of
  over-estimating is zero; here it costs a tier change and six envelope round-trips.
- Consider making `exceeds_bash_ceiling` **sticky-but-revisitable**: re-measure once under low
  contention before accepting a permanent tier promotion.

## Related

- `2026-07-27-00-001` — a GREEN verify reported as `timeout/-1` (the same inverse polarity,
  seen from the reporting side).
- `2026-08-01-13-001` — the wrapper stamps `status=timeout exit_code=-1` over a pytest run that
  reached its own green summary. That lesson was reviewed by this plan's lessons-housekeeping
  and **retained** as still-live; this finding is the downstream consequence of it being live.
