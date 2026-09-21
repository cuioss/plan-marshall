envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:44:51Z

component=plan-marshall:phase-3-outline
category=improvement
created=2026-09-15
bundle=plan-marshall

# Record per-file assessments in the deep lane so outline-vs-shipped can measure

## Context

This plan ran the deep planning lane and produced a 100 KB solution outline with 12 deliverables, yet left no per-file assessments store at all: `assessments_store_present: false`, `assessments_read: 0`, `assessed_path_count: 0`. The outline-vs-shipped aspect therefore compared 79 realized paths against an empty assessment set and could report only `touched_but_unassessed: 79 of 79`, with both other outcome classes measured over a denominator of zero.

## Root cause

Recording an assessment is not a step the deep lane performs — the aspect that consumes them exists, and the store it reads has a defined shape, but nothing in phase-3-outline writes a row. The aspect degraded honestly (it published its denominators rather than reporting three confident zeros), which is why this surfaces as a measurement gap rather than a false pass.

## Solution

Have the deep lane record an assessment per file it considered — at minimum the certain-include and certain-exclude verdicts the aspect's two other outcome classes are keyed on. A deep-lane outline already reasons about each candidate file; persisting that verdict is what makes the include-unrealised and exclude-violated classes measurable.

## Impact

On every deep-lane plan, two of the aspect's three outcome classes have a zero denominator and the third absorbs the entire footprint. The aspect reports and never gates, so nothing breaks — but it also cannot tell anyone anything.

## Evidence

- aspect: outline_vs_shipped — `assessments_store_present: false`, `assessments_read: 0`, `comparison: measured`, `include_unrealised 0 of 0`, `exclude_violated 0 of 0`, `touched_but_unassessed 79 of 79`
- `status.metadata.planning_lane: deep`
