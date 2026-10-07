envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:43:02Z

# Emit the [DISPATCH] line on every loop-back re-fire, not only on first firing

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

The execution-context dispatch audit consumes `[DISPATCH]` work-log lines as its sole
evidence surface. Scanning this plan's work log over the window 02:04Z-14:35Z found four
real execution-context dispatches that produced an envelope completion with **no**
`[DISPATCH]` emission:

- `project:finalize-step-plugin-doctor` completed at 10:55:01Z; its only `[DISPATCH]` line is at 03:02:30Z.
- `finalize-step-simplify` completed at 11:16:30Z; its only `[DISPATCH]` line is at 04:19:43Z.
- `automatic-review` completed at 12:06:40Z and 13:28:18Z; its only `[DISPATCH]` line is at 05:08:42Z.
- `phase-5-execute` loop-back re-entry #2 at 12:28:48Z; loop-back #1 correctly emitted one at 07:55:52Z.

Each re-fire is a genuine dispatch — it carries its own execution-context envelope
completion, and three of the four carry their own in-envelope `[SKILL] Loaded` lines.

## Root cause

All four share one shape: the **first** firing of a dispatched step emits its
`[DISPATCH]` line and every **loop-back re-fire** of that same step does not. The
emission lives in the caller's first-firing branch rather than in the dispatch primitive,
so re-entry paths bypass it.

The consequence is directional and bad: a plan with zero loop-backs audits clean by
construction, and a plan with N loop-backs silently under-reports its dispatch count.
The audit's clean verdict is therefore weakest on exactly the plans that dispatched the
most. Here the under-count is 4 of 13 real dispatches in the scanned window — 31%.

## Proposed action

Move the `[DISPATCH]` emission into the dispatch primitive itself so it is a property of
dispatching rather than of the caller remembering to log. Add a loop-back regression case
asserting that a step re-fired after a loop-back emits a second `[DISPATCH]` line
carrying the same role.

## Evidence

- logs/work.log — the four envelope completions listed above, each with no preceding `[DISPATCH]` line for that firing.
- logs/work.log 07:55:52Z vs 12:28:48Z — the same step, same role, one loop-back emitted and one not; the cleanest matched pair.
- `plan-retrospective/standards/execution-context-dispatch-audit.md` § Detection Logic — `shape_violation` is the declared category for a spawn with no matching emission.
