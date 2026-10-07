envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:56:57Z

# Partiality verdict cannot see a stale-closed phase, only a never-closed one

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

`work/metrics.toon` for this plan was last written at `2026-08-09T14:14:00Z`. The plan ended at
`20:43:50Z` — six and a half hours and one full phase-6 → phase-5 loop-back later. The file's
`5-execute` row carries `end_time: 2026-08-09T14:14:00Z` and `close_count: 2`, and the top-level
verdict reads `partial: true` with `unrecorded_phases: 6-finalize`.

But `5-execute` was entered a **third** time. The loop-back re-entered it at `18:17:18Z` and exited
at `19:06:41Z`, executing TASK-006 through TASK-010 and recording a 314,870-token dispatch boundary.
That close is absent from the metrics row, and `unrecorded_phases` does not name `5-execute`.

The corroborating detail is exact: `work/metrics-dispatch-boundaries-5-execute.toon` holds four rows
(421190, 168435, 314870, 0), while the metrics row reports `dispatch_boundary_rows_recorded: 2` and
`dispatch_boundary_total: 589625` — precisely the sum of the first two. The third round's tokens are
on disk in the boundary file and absent from every aggregate computed off the metrics row.

## Root cause

`generate`'s partiality rule keys a phase's *recorded* status solely off the presence of an
`end_time` marker. That predicate answers "was this phase ever closed?" and is read as though it
answered "is this phase's row current?". A loop-back produces a row that satisfies the first and
fails the second, and no field distinguishes them.

## Proposed action

Give the partiality verdict a **staleness** discriminator alongside its existence one. Two
independent facts are already on disk and can be compared without new observation:

1. `close_count` versus the number of `[STATUS] ... Re-entering execute phase` / `set-phase` entries,
   or more robustly versus the row count in `metrics-dispatch-boundaries-{phase}.toon`. A phase whose
   boundary file holds more rows than `dispatch_boundary_rows_recorded` is provably stale.
2. `metrics.toon`'s own `updated` timestamp versus the plan's latest activity.

Report the result as a distinct list — `stale_phases[]` beside `unrecorded_phases[]` — so a reader
can tell "this phase was never closed" from "this phase's row predates work it should cover". The
same fix removes the second-order problem: `total_tokens (n=5/6)` currently presents a total whose
denominator is right and whose numerator is wrong.

The loop-back exit is a scripted transition (`Phase: 5-execute -> 6-finalize`, logged at `19:06:41Z`),
and `manage-metrics boundary-status` already exists to classify exactly this half-stamped boundary.
Calling it on that path and stamping the missing close is deterministic, not a judgement.

## Evidence

- `work/metrics.toon` — `updated: 2026-08-09T14:14:00Z`; `[5-execute] end_time: 2026-08-09T14:14:00Z`,
  `close_count: 2`, `dispatch_boundary_rows_recorded: 2`, `dispatch_boundary_total: 589625`;
  top-level `partial: true`, `unrecorded_phases: 6-finalize`.
- `work/metrics-dispatch-boundaries-5-execute.toon` — 4 rows; the third
  (`2026-08-09T18:59:57Z, voluntary_checkpoint, 314870`) is unaccounted for.
- `logs/work.log` — `18:17:18Z [MANAGE-STATUS] Phase: 6-finalize -> 5-execute`;
  `19:06:41Z [MANAGE-STATUS] Phase: 5-execute -> 6-finalize`.
- aspect `plan_efficiency` — finding `STALE_CLOSE_INVISIBLE_TO_PARTIALITY`.

## Why this belongs to truthful-signals

`partial: true` was introduced so a total could never be read as complete when it was not. It does
that job for a phase that never closed. This is the adjacent case it cannot see, and it fails in the
more dangerous direction: the phase is reported as *recorded*, so the caveat that exists points at
the wrong row.
