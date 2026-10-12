envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:37Z

component=plan-marshall:plan-marshall
category=improvement
created=2026-10-09

# Pass step id and context-load figures on every record-dispatch-boundary call

## Context

Plan `plan-lb-29-harness-sync` recorded 38 dispatch-boundary rows (2 in 4-plan, 17 in 5-execute, 19 in 6-finalize). Every row has an empty `step_id` and all four context-load columns read `unmeasured`. The retrospective's firing comparison therefore paired zero boundary rows with execution-log rows in all three phases (10 unpaired execution rows in execute, 27 in finalize), and the cost of context position per dispatch is unmeasured for the whole plan.

## Root cause

The main session calls `record-dispatch-boundary` with the termination cause and the three totals only. `--step-id` and the four `--*-tokens` flags are optional, so their omission is silent: the call succeeds and writes a row that can be counted but not joined.

## Proposed action

- In the workflow text for every call site (task-planning, execute and finalize dispatch returns), write the call with `--step-id {step key}` and state that it is passed on every call that has a step.
- Forward the context-load split from the dispatch's usage record when the platform provides it; when it does not, say so once in the workflow so the `unmeasured` columns are a known limit and not an omission.
- Have `record-dispatch-boundary` return a warning field when `--step-id` is absent for a phase whose execution log carries step ids.

## Evidence

- aspect: execution_context_dispatch_audit — firing comparison: `keyless_boundary_rows` 2, 17 and 19; `paired_firings: 0` in every phase; channel confidence `low` (8 distinct finalize dispatch lines against 27 completions).
- aspect: log_analysis — `context_position_cost`: 38 rows, 0 measured, 38 unmeasured; every boundary row lists all four context-load columns as unmeasured.
