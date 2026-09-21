envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T09:05:54Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# analyze-logs reports build_count 0 against 84 recorded pyproject_build calls

## Context

`analyze-logs` emitted `build_count: 0` for this plan. The same run's script-execution
log carries **84** `pyproject_build` calls totalling 4,122,990 ms — 48% of all script
time in the plan, and the single largest cost line in the run.

The two figures come from the same substrate and disagree completely. The retrospective
that consumed `analyze-logs` had to read the build cost off the script-cost rollup
instead, and did so by hand; the build-minimality facet that `build_count` exists to
feed had no population at all.

A `build_count: 0` is not obviously wrong to a reader. It reads as "this plan ran no
builds" — a plausible sentence about a plan — rather than as "the counter did not match
anything". That is the same confident-zero shape the epic keeps finding: a well-formed
success carrying a count nobody can distinguish from a real absence.

## Root cause

Not established from the outside. The observable is that the marker `build_count`
matches is not the marker the build calls actually emit for this run. This plan's builds
were **daemon-routed** through the build server rather than executed inline, so the
wrapper's own emission shape differs from the direct-execution shape — that is the most
likely discriminator, and it is testable by counting the same log both ways.

Worth checking against the sibling defect that was already fixed one commit earlier
(`1169fb5b`, finding `34fe2d`): the daemon-routed executed-test count was lost on
exactly the same seam, because the outer consumer re-parsed a log holding the wrapper's
TOON rather than the raw tool output. If `build_count` reads the same log the same way,
it is the same defect in a second consumer.

## Proposed action

Count builds from a marker the daemon-routed path actually emits, and make the counter
state which kind of zero it is: a plan that genuinely ran no build and a counter that
matched nothing must not both render as `build_count: 0`. Pair the count with the
population it was computed over, as the other analyze-logs figures already do.

## Evidence

- `analyze-logs` → `build_count: 0` for this plan
- script-cost rollup, same run → `pyproject_build`, 84 calls, 4,122,990 ms, 48% of script time
- corroborating seam: `1169fb5b` / finding `34fe2d` fixed the identical outer-consumer
  re-parse for the daemon-routed executed-test count
- observed by the retrospective and independently by the orchestrator
