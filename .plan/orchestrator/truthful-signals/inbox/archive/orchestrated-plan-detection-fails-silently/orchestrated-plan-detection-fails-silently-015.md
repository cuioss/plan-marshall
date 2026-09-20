envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:18:56Z

component=plan-marshall:manage-metrics
category=improvement
bundle=plan-marshall

# metrics.md omits 6-finalize entirely, so a plan cannot state its own token cost and the budget anchors cannot be applied

## What happened

PLAN-114's `metrics.md` reports:

```
| **Total** | 56m43s (n=3/6) | 1h23m (n=5/6) | 910,552 (n=3/6) | 331 (n=3/6) |
### 6-finalize
- Start: 2026-07-29T14:40:16Z
- End: -
```

910,552 tokens over three of six phases, with 6-finalize blank.

The plan's finalize phase actually consumed **976,792 tokens across nine dispatched envelopes** — more than the entire refine + plan + execute spend combined. The true total is at least **1,887,344**, which crosses the `single_module + bug_fix` **error** anchor (1.3M), where the reported 910,552 sits below even the warning anchor (800K).

The data exists. `work/metrics-dispatch-boundaries-6-finalize.toon` holds all nine rows with `total_tokens`, `tool_uses`, and `duration_ms`. `analyze-logs` reads and reports them. Nothing folds them into `metrics.md`.

## The consequence

The retrospective's plan-efficiency aspect is required to compare `totals.tokens` against calibration anchors and emit `[BUDGET]` findings. Reading `metrics.md` as instructed yields **no anchor trip at all**. Only by hand-summing dispatch-boundary rows out of a *different* aspect's fragment does the plan turn out to be over the error threshold by 45%.

So the budget-anchor mechanism — a core measurement arm — silently returns "under budget" for every worktree plan whose cost is concentrated in finalize. And finalize is where cost concentrates: 52% here.

## Root cause

`record-metrics` runs at finalize step 20 of 22 and writes the phase's *start*, but the phase is not over when it writes, so the end/token fields stay blank and are never revisited. The `(n=3/6)` marker is honest about phase coverage, but it is a coverage caveat on a number that is then consumed as a total.

## Corrective rule

1. **Fold `work/metrics-dispatch-boundaries-{phase}.toon` into `metrics.md` at `record-metrics` time** for every phase, 6-finalize included. The rows are already written by `record-dispatch-boundary`; this is aggregation, not new instrumentation.
2. **Mark the total's completeness explicitly in a machine-readable field**, not only in a `(n=3/6)` string inside a markdown table cell. A consumer applying budget anchors must be able to branch on `token_total_complete: false` rather than parse prose.
3. **The plan-efficiency aspect must refuse to emit a "within budget" verdict on an incomplete total.** Under-budget on partial data is not a pass; it is an unmeasured plan.

## Aggravating factor observed on the same run

1-init and 3-outline carry no token data at all, because `session_id` was not captured until 14:11:43 — 54 minutes into the run (`work.log` line 3 emitted the WARNING at 13:18:56 and the run continued). So the reported total is missing two phases for one reason and a third phase for another, and the single `(n=3/6)` marker covers both causes indistinguishably.

## Why it matters for truthful signals

`910,552 (n=3/6)` is not a lie, but it is used as a total by the one consumer designed to catch runaway plans, and as a total it understates by 2×. **A number carrying a coverage caveat in its label will be read as a number.** Either complete it or make the incompleteness structurally unignorable.

## Evidence

- `metrics.md` — 6-finalize row blank, `End: -`
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 9 rows summing to 976,792
- `plan-efficiency` fragment — anchor `single_module+bug_fix error at 1.3M` crossed only after manual reconstruction
