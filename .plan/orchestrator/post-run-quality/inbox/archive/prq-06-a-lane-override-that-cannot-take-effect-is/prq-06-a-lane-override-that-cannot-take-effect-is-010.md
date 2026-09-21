envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:53Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=plan_efficiency,log_analysis

# Nearly four fifths of script wall time is spent waiting, not computing

## Context

The plan's script cost rollup over 2,051 calls totals 14,423,580 ms. The three costliest scripts are all waits:

| Script | calls | cumulative_ms | share | max_ms |
|--------|------:|--------------:|------:|-------:|
| `build-server-client:build_server` | 24 | 3,959,140 | 27.4% | 601,430 |
| `tools-integration-ci:ci` | 57 | 3,931,890 | 27.3% | 572,140 |
| `phase-6-finalize:ci_complete_precondition` | 8 | 3,335,840 | 23.1% | 573,950 |

Combined: **77.8%** of measured script time. Only 50 of 2,051 calls reached the 30-second ceiling at all, so this is a small number of very long stalls, not broad slowness.

Two specific shapes stand out:

- `ci_complete_precondition` cost 3.3M ms across **8 calls** — an average of 417 seconds each — with three individual calls at roughly 573 seconds, sitting just under a 600-second ceiling.
- `build_server`'s maximum is 601,430 ms, i.e. a long-poll that ran out its full budget and returned on timeout rather than on a result.

The plan's own wall-versus-worked split corroborates it from the other side: 29h16m elapsed against 5h31m worked, 25h22m idle (87%).

## Root cause

Long-poll budgets are sized just under the harness timeout ceiling, so every poll that misses converts into a near-maximal stall rather than a quick negative. A `ci_complete_precondition` that cannot yet conclude burns ~573 seconds finding that out, and it did so three times.

Some of this wall time is genuinely unavoidable — one of the two recoverable operator decisions on this plan was a deliberate wait for CodeRabbit's hourly quota window, which is a correct call under the standing review-discipline protocol. But a deliberate hour-long wait for a rate window is a different thing from eight precondition polls averaging seven minutes each, and the rollup currently cannot tell them apart.

## Proposed action

1. Separate *deliberate waits* (rate-window holds, merge-queue waits) from *poll misses* in the cost rollup, so a plan that waited correctly does not read the same as one that stalled. A `wait_reason` on the recorded call would do it.
2. Give `ci_complete_precondition` an early-negative path: when the precondition is not merely unresolved but *cannot* resolve yet (no run started, SHA mismatch), return immediately instead of polling to the ceiling.
3. Re-examine the ~600-second budgets. A poll budget at 95%+ of the harness ceiling leaves no room to report a miss and makes every miss maximally expensive.

## Evidence

- aspect: log_analysis — `script_cost_rollup` `ranked[10]`, top three at 27.4% / 27.3% / 23.1%; `calls_at_or_over_ceiling: 50` of `total_calls: 2051`
- aspect: log_analysis — `slowest_scripts`: `build_server` 601,430 ms, `ci_complete_precondition` 573,950 ms and 573,190 ms
- aspect: plan_efficiency — `idle_share: 0.87`; wall 105,412 s against worked 19,875 s
- aspect: chat_history_analysis — the operator's recorded ruling: "Wait for CodeRabbit's quota window (Recommended)"
