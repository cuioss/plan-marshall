envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:22:37Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=finalize-step-contract-guard-residue

# Let enrich bill the terminal phase whose window record-metrics closes after it

## Context

`manage-metrics enrich` attributes the four-field `message.usage` view (input / output / cache_read / cache_creation) to a phase by that phase's recorded time window. A window needs an `end_time`, and `6-finalize` has none until `default:record-metrics` performs the authoritative close at finalize order **998**.

Every consumer that reads billing runs earlier. `plan-retrospective` sits at order **995**. So on every plan, the phase that closes last is the phase that can never be billed by the retrospective that reports on it.

On this plan the omission is not marginal — it is the largest single item:

- `6-finalize` dispatched **2,635,188** tokens, 48 pct of the plan's 5,483,351 dispatched total, and more than `5-execute` (1,210,592) and `4-plan` (535,462) combined.
- Its `metrics.md` Phase Details block carries no `Main-context-window usage`, no `Billing-weighted total`, and none of the exploration / cache-residency bullets every other phase carries.
- The reported plan billing total, **63,456,072**, is stamped `population_count: 5` of denominator 6.

For scale: `5-execute` dispatched 1.21M tokens and cost 35.3M billing. `6-finalize` dispatched 2.18x that. The published 63.5M is plausibly under half the real cost, and nothing in the figure says so beyond the population marker.

## Root cause

Attribution requires a closed window; the close is ordered after every reader. The ordering is not accidental — `record-metrics` must run late precisely so it can fold in the retrospective's own spend — so the fix cannot simply be to move it earlier.

## Proposed action

Give `enrich` an open-window mode: when a phase has a `start_time` and no `end_time`, attribute usage from `start_time` to now and record the result with an explicit `window: open` / floor marker, exactly as the accumulator reconcile already does for `total_tokens` at Step 2.5 of the retrospective workflow. The authoritative close at order 998 then overwrites the floor, as it already does for the token total.

Failing that, have `generate` render the billing cell for an unclosed phase as an explicit `unbillable (window open)` rather than `-`, so the omission is legible rather than looking like a phase that cost nothing.

## Evidence

- aspect: plan_efficiency — `billing_composition.missing_phase: 6-finalize`, `population_count: 5` of 6
- artifact: `metrics.md` Phase Details — `6-finalize` carries `End: -` and no four-field block, while all five other phases carry one
- aspect: plan_efficiency — `6-finalize` is the `dominant_phase` at 2,635,188 dispatched tokens, `max_phase_token_share: 0.48`
- workflow: `plan-retrospective/SKILL.md` order 995 vs `default:record-metrics` order 998
