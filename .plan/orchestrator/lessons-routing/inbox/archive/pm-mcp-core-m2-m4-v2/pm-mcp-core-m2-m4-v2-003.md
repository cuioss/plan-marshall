envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T20:34:16Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=plan-v2-93-http-tests-annotations

# Keep each phase window intact across a finalize loop-back into execute

## Context

In plan-v2-93 finalize looped back into 5-execute (TASK-11 for the Sonar gate) and then re-entered 6-finalize. `work/metrics.toon` shows 5-execute closed three times with the same `start_time` 12:55:07 each time (ends 14:38:48, 14:43:04, 16:22:39), and 6-finalize's `start_time` is 16:22:39. The first finalize pass (about 14:43 to 16:12: reviews, push, PR, CI) therefore has no window of its own: its wall time is counted into 5-execute (3h27m wall, 2h18m idle) and the 6-finalize start was overwritten.

## Root cause

The re-entry `start-phase` for 5-execute did not re-stamp its start, while the re-entry into 6-finalize did, overwriting the original finalize start. Per-phase windows are single intervals, so a loop-back cannot be represented.

## Proposed action

On re-entry, keep a list of intervals per phase (the `phase_intervals` field already exists) and derive wall, idle and token attribution from the intervals, never from a single overwritten `start_time`. At minimum, never overwrite an existing `start_time` of a phase that has not closed.

## Evidence

- plan-efficiency: 5-execute wall window 12:55-16:22 absorbs the first finalize pass
- logging-gap-analysis: 6-finalize start_time re-stamped at the 16:22:39 re-entry
- metrics.toon: `phase_intervals` lists three 5-execute intervals all starting 12:55:07
