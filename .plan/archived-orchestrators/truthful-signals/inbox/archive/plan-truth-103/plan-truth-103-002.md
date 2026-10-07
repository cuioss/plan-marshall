envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:00:37Z

# re_entered_phases reports clean on a run with seven loop-backs

component: plan-marshall:manage-metrics
category: bug
confidence: high
source_plan: plan-truth-103
source_aspects: logging_gap_analysis, invariant_summary, plan_efficiency

## Context

`manage-metrics/SKILL.md` states that `close_count` "is written at the write
site" and that `re_entered_phases` is therefore "the **authoritative** re-entry
signal", explicitly ranking it above the weaker `boundary_monotonicity`
timestamp inference.

On plan-truth-103 `manage-metrics generate` returned:

```
re_entered_phases[0]:
boundary_monotonicity[0]:
```

and every one of the six rows in `work/metrics.toon` carries `close_count: 1`
and `value_scope: single_close`.

The same plan's `status.json` carries:

```
loop_back_iteration: "7"
loop_back_reentry:
  from_phase: 6-finalize
  to_phase: 5-execute
  at: "2026-09-13T10:04:51Z"
```

The authoritative signal reports no re-entry on a plan whose own status record
documents one, after seven loop-back iterations.

## Root cause

Nothing on the loop-back re-entry path calls `end-phase` / `phase-boundary` for
the re-entered phase, so `close_count` is never incremented. The accumulate-on-
re-entry machinery in `manage-metrics` is correct and complete; it is simply
never invoked, because the re-entry writes `status.metadata.loop_back_reentry`
and calls `set-phase`, not a metrics boundary.

## The concrete corruption it produces

`5-execute` carries `end_time: 2026-09-12T17:36:26Z`. Its own dispatch-boundary
file `work/metrics-dispatch-boundaries-5-execute.toon` carries a row timestamped
`2026-09-13T10:28:47Z` (`clean_exit_queue_empty`, 197,383 tokens) — seventeen
hours **after** the phase is recorded as closed.

So the row mixes two incompatible scopes:

- `duration_seconds: 13823.0` and `idle_duration_ms` are scoped to the FIRST
  execute window and silently exclude the second pass;
- `dispatch_boundary_total: 1475194` sums every boundary row regardless of
  window and therefore INCLUDES it.

A consumer reading the row cannot tell, and `value_scope: single_close` actively
asserts that no such split exists.

## Proposed action

Either (a) have the loop-back re-entry path call `phase-boundary --prev-phase
6-finalize --next-phase 5-execute` so `close_count` records what happened, or
(b) if the re-entry is deliberately not a metrics boundary, make `generate`
cross-read `status.metadata.loop_back_iteration` /
`status.metadata.loop_back_reentry` and refuse to publish
`re_entered_phases[0]` when they contradict it — reporting the contradiction
rather than the clean zero. (a) is preferred: it makes the row correct rather
than making the report defensive about a row it knows is wrong.

## Evidence

- `work/metrics.toon`: all six rows `close_count: 1`, `value_scope: single_close`
- `manage-metrics generate` return: `re_entered_phases[0]`
- `status.json`: `loop_back_iteration: "7"`, `loop_back_reentry.at: 2026-09-13T10:04:51Z`
- `[5-execute].end_time: 2026-09-12T17:36:26Z` vs a 5-execute dispatch-boundary row at `2026-09-13T10:28:47Z`
- `manage-metrics/SKILL.md` § generate: "Because `close_count` is written at the write site, this is the **authoritative** re-entry signal"
