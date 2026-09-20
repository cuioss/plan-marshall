envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:31Z

# First entry into 5-execute logs 'Re-entering', never 'Starting'

component: plan-marshall:phase-5-execute
category: bug
confidence: high
source: plan-retrospective (aspects: log-analysis, logging-gap-analysis)
suggested_epic: truthful-signals

## Context

`analyze-logs` reports for this plan:

```
dispatch_clustering:
  inferred_dispatches: 2
  starting_markers: 0
  re_entering_markers: 2
```

The plan entered 5-execute exactly twice: first at 13:14 (fresh, after the 13:12:21 `[DISPATCH]`), then again at 16:18 after the finalize loop-back. Both entries logged `Re-entering execute phase`. The first-ever entry — `[2026-08-01T13:14:11Z] ... Re-entering execute phase - 3 tasks pending` — is a first entry, not a re-entry.

## Root cause

The Starting/Re-entering discriminator is not keyed on whether the phase was previously entered. The message text pairs `Re-entering` with a pending-task count in both cases, which is consistent with the predicate being "the task queue is non-empty" rather than "this phase has a prior close". Any plan whose first phase-5 dispatch finds pending tasks — i.e. every normal plan — mislabels its first entry.

The consequence is that the RE_ENTRY_COVERAGE invariant in `plan-retrospective/references/logging-gap-analysis.md` cannot be evaluated: it expects `clusters - 1` Re-entering lines, so 2 clusters should yield 1. Observing 2 makes the check fire a warning on a plan that actually re-entered exactly once and logged it. The detector is correct; the emitter is wrong; the warning lands on the wrong side.

## Proposed action

1. Key the discriminator on prior phase closure (a recorded 5-execute `end_time` in `work/metrics.toon`, or a prior `[STATUS] ... execute phase` line in the plan's own work.log) rather than on the pending-task count.
2. Add a regression test: a fresh plan's first 5-execute dispatch emits `Starting`, and only a dispatch following a recorded close emits `Re-entering`.
3. Note for the fixer: `starting_markers: 0` across the whole corpus is the cheap corpus-wide detector for this — if the archived-plan audit shows zero `Starting` markers on every plan, the defect predates this run and is universal, not plan-specific. That population check has NOT been run and should not be assumed.

## Evidence

- aspect: log-analysis — `starting_markers: 0`, `re_entering_markers: 2`, `inferred_dispatches: 2`
- `logs/work.log:85` — `[2026-08-01T13:14:11Z] ... Re-entering execute phase - 3 tasks pending` (first entry)
- `logs/work.log:312` — `[2026-08-01T16:18:30Z] ... Re-entering execute phase - 5 tasks pending` (genuine re-entry after loop-back)
- `logs/work.log:77` — the preceding `[DISPATCH] ... role=phase-5-execute` at 13:12:21, the first in the run
