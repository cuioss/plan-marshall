envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:40Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Forward the bare step id on every record-dispatch-boundary call

## Context

This plan recorded 23 dispatch-boundary rows (1 in 4-plan, 4 in 5-execute, 18 in 6-finalize). 21 carry no step id. Of the two that do, `create-pr` pairs with its execution-log row and `plan-marshall:automatic-review` does not, because the execution log holds the bare id `automatic-review`. One finalize firing of 18 can be joined between the two ledgers.

All 23 rows also record the four context-load columns as `unmeasured`, so cache-read cost per tool use is unmeasured for every phase.

## Root cause

`manage-metrics record-dispatch-boundary` documents: "Forward the dispatch's step key on EVERY call". The callers - the finalize dispatcher and the orchestrator's plan and execute hand-off - mostly omit `--step-id`, and where one is passed its spelling is not the one `record-step` writes. The four context-load flags are never passed. Whether the workflow documents omit the flag or the orchestrator dropped it was not established.

## Proposed action

1. Make every `record-dispatch-boundary` call site in the finalize and execution workflows pass `--step-id`, in the same spelling `record-step` uses for that step.
2. Normalize or reject a prefixed id at the recorder so the two ledgers cannot disagree on spelling.
3. Pass the context-load figures where the dispatch return carries them; where it does not, say so once in the workflow so the unmeasured columns are a stated limit.

## Evidence

- dispatch-audit `firing_comparison`: 6-finalize `keyless_boundary_rows: 16`, `paired_firings: 1`, `unpaired_boundary: [plan-marshall:automatic-review]`; 5-execute `keyless_boundary_rows: 4`; 4-plan `keyless_boundary_rows: 1`
- log-analysis `context_position_cost`: `measured_rows: 0`, `unmeasured_rows: 23`
- dispatch-audit `channel_completeness`: confidence `low`, ratio 0.233
