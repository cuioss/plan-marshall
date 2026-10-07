envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:46:01Z

component=plan-marshall:manage-metrics
category=bug

# Three artifacts disagree about this plan's token cost, and one labels a phase sum as the plan total

Three of this plan's own artifacts answer "what did this plan cost?" with three different numbers, none of which is the answer.

**1. `routing-decisions` — `cost_preview.actual_tokens: 784904`.** The field name says actual, plan-scoped. The number is exactly the sum of the eight `6-finalize` dispatch-boundary rows:

```
113512 + 80104 + 162484 + 67204 + 99225 + 115367 + 73431 + 73577 = 784904
```

It is a **single phase's** figure carried under a plan-scoped label, and it understates the plan by roughly 3.3×. Nothing in the field name or its neighbours signals the restriction.

**2. The `6-finalize` accumulator — `total_tokens: 987327`, `samples: 9`.** This measures the *same phase* as the number above and disagrees with it by **202,423 tokens (21%)**. Nine samples against eight dispatch-boundary rows. Two independent recorders, one phase, no reconciliation.

**3. `metrics.md` — `Total: 1,603,563 (n=4/6)`.** Honest about being partial — it carries the `n=4/6` marker and a "Partial: unrecorded phases — 6-finalize" banner. This is the one artifact that labels its own incompleteness, and it is the one a reader is least likely to mistake for the total. But it is also the number rendered in the largest, boldest cell of the report table.

The plan's actual cost, reconstructed by hand across artifacts, is **≈2,590,890 tokens** — and even that is a floor, because `1-init` recorded no token sample at all. (That gap has its own upstream cause, visible in `work.log` line 3: `session_id not captured at plan-init`. No session id at init means no transcript to read token usage from, so the phase records duration but no tokens.)

For the epic's purposes the pattern matters more than the arithmetic: **every one of these is a confidently-named field whose scope is narrower than its name.** `actual_tokens` is a phase sum. `Total` is 4 phases of 6. Only one of the three admits it.

## Solution

- **Rename or rescope `cost_preview.actual_tokens`.** If it is a finalize-phase figure, name it so (`finalize_dispatch_boundary_tokens`). A field named `actual_tokens` on a plan-scoped fragment will be read as the plan's actual tokens, and there is no reason for a reader to suspect otherwise.
- **Reconcile the two 6-finalize recorders.** The accumulator and the dispatch-boundary ledger measure the same phase and must not diverge by 21% silently. Either establish one as authoritative and derive the other, or emit both with an explicit divergence field so a consumer can see the disagreement rather than pick whichever it read first.
- **Give `manage-metrics` a single `totals` verb** that returns one authoritative figure plus an explicit `unrecorded_phases[]` list — so no consumer ever hand-sums across `work/metrics-*.toon`, which is what this retrospective had to do.
- **Never render a partial total without its qualifier adjacent to the number.** `metrics.md` does this correctly with `n=4/6`; the pattern should be mandatory wherever a total is emitted, not a courtesy of one renderer.
- **Fix the init-phase token gap at its cause.** The `session_id` should be captured at plan-init; the late capture at 14:51 (an hour and a half into the run) is why `1-init` has no token sample and why every ratio computed from the total is a floor.

## Evidence

- aspect: `routing-decisions` — `cost_preview: actual_tokens: 784904, predicted_tokens: null`
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 8 rows summing to exactly 784904
- `work/metrics-accumulator-6-finalize.toon` — `total_tokens: 987327, samples: 9`
- `metrics.md` — `**Total** | ... | **1,603,563 (n=4/6)**`, banner "Partial: unrecorded phases — 6-finalize"
- `work.log:3` — `[WARNING] session_id not captured at plan-init`; `work.log:74` — session_id metadata finally written at 14:51:55
- aspect: `plan-efficiency` — `token_accounting_divergence.delta: 202423`
