envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:32Z

component=plan-marshall:phase-6-finalize
category=bug
title=plan-retrospective at step 20 cannot see metrics recorded at step 23 — finalize-ordering, second instance

# plan-retrospective cannot see the metrics recorded after it

## The defect

The composed finalize step order for PR #1075 places:

- `plan-marshall:plan-retrospective` at **position 20**
- `record-metrics` at **position 23**

`plan-retrospective`'s plan-efficiency aspect reads `metrics.md`. On this plan `metrics.md`
was written at 2026-08-01T18:35:52Z — the instant finalize *began* — and carries:

```
> Partial: unrecorded phases — 6-finalize
| **Total** | 5h29m (n=4/6) | 8h6m (n=5/6) | 2h37m (n=5/6) | **4,666,704 (n=4/6)** | 1873 (n=4/6) |
```

Reconstructing phase 6 from `execution.toon`'s `execution_log` gives **1,564,096 tokens across
11 attributed steps**, so the true plan total is ~6,230,800. `metrics.md` understates the plan
by **25.1%**, and it does so at *every* finalize-step retrospective, by construction — not
occasionally, not on this plan only.

The `Partial:` banner correctly names the gap. No consumer acts on it.

## Why this is a lesson and not a one-off

This is the **second instance of the finalize-ordering archetype**. The first was PLAN-10
(shipped as #1036): *a plan that fixes a finalize-time component cannot have that fix exercised
by its own finalize*, because the cache syncs at step 19 while the retrospective runs at 17.

Same structure, different pair: **a finalize step that consumes an artifact produced by a later
finalize step reads a stale or empty artifact, silently, forever.** The step list is a total
order and nothing checks producer-before-consumer across it.

## Do this instead

Three options, in increasing order of generality:

1. **Narrow fix** — move `record-metrics` before `plan-retrospective` in the composed order.
   Cheap, and wrong-ish: it fixes this pair and leaves the class open.
2. **Better fix** — have `plan-retrospective` read `execution.toon`'s `execution_log` directly
   for phase-6 attribution instead of `metrics.md`. The `execution_log` is written
   incrementally by `record-step` and is complete for every step that has already run, which
   is exactly the population a retrospective is entitled to see.
3. **General fix** — declare producer/consumer artifact dependencies on finalize steps and
   have manifest composition **reject or reorder** a step list where a consumer precedes its
   producer. This is the only option that closes the archetype rather than an instance.

Option 3 is the one worth a plan spec. The archetype is now at n=2 with two different artifact
pairs (plugin cache / retrospective; metrics / retrospective), and `plan-retrospective` is the
consumer in both — it sits late enough to want everything and early enough to get nothing.

## Related

- PLAN-10 / #1036 — the first instance.
- The sibling `cost_preview.actual_tokens` finding is a *third* face of the same artifact:
  `check-routing-decisions` sums the `execution_log` (finalize-only rows) and reports it under
  a field name that reads as whole-plan actual cost.
