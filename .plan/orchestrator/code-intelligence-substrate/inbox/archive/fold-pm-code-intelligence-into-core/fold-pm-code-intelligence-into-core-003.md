envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:51Z

# A finalize loop-back leaves 6-finalize half-stamped and clamps its worked time

## Context

This plan looped back from `6-finalize` into `5-execute` (`status.metadata.loop_back_iteration: 1`; `5-execute` carries `close_count: 2`). The `6-finalize` row, however, reads `close_count: 1`, `value_scope: single_close`, `start_time: 18:37:32Z`, `end_time: 19:52:24Z`, `duration_seconds: 4492`, `idle_duration_ms: 0`.

That row is contradicted by its own dispatch-boundary ledger. `work/metrics-dispatch-boundaries-6-finalize.toon` holds 10 rows spanning `15:10:32Z` to `19:14:39Z` — **9 of the 10 are timestamped before the row's recorded `start_time`**. The first finalize entry was never closed, so its wall span was dropped and `start_time` was overwritten by the re-entry.

## Root cause

The loop-back path calls `start-phase` on re-entry into `6-finalize` without an intervening `end-phase` for the first entry, which is the half-stamped boundary `boundary-status` exists to detect. Because `close_count` stays at 1, none of the re-entry machinery fires: `re_entered_phases` lists only `5-execute`, `value_scope` reads `single_close`, and the wall span never accumulates.

The consequence propagates into the worked figure. `agent_duration_ms` is recorded as `4492000` — exactly `duration_seconds x 1000`, i.e. the clamp bound it to the short wall span — while the phase's own 10 boundary rows sum to `4568807` ms. So `totals_worked_ms` is a floor, and the `Worked <= Reported (wall)` invariant holds only because both sides were shrunk together.

## Proposed action

Stamp the `6-finalize` close on the loop-back edge (or call `boundary-status` on finalize re-entry and stamp the missing `phase-boundary`), so the phase accumulates like `5-execute` does. Separately, consider making the clamp report when it fires: a clamped `agent_duration_ms` that exactly equals the wall span is indistinguishable from a genuine measurement, which is how this stayed invisible.

## Evidence

- aspect: plan_efficiency — `duration_seconds=4492` vs boundary rows spanning `15:10:32Z-19:14:39Z`
- aspect: plan_efficiency — `agent_duration_ms=4492000` < `boundary_row_sum=4568807`
- `work/metrics.toon` `[6-finalize]`: `close_count: 1`, `value_scope: single_close`, `idle_duration_ms: 0`
- `metrics.md` renders `6-finalize` as `Worked 1h14m / wall 1h14m / Idle -` — a confident, fully-worked-looking row produced by a clamp
- `any_phase_missing_end_time: false` — the phase reports complete while it was in fact still open (this retrospective ran at 21:02Z)
