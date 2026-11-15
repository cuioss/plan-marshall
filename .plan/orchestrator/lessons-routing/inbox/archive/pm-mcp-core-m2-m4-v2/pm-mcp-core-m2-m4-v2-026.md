envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T09:16:43Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall

# Forward --step-id and the context-load totals on every record-dispatch-boundary call

## Context

Observed in PLAN-V2-40 (plan-v2-40-envelope-packing, PR #402) by the plan retrospective. All 14 dispatch-boundary rows of the plan (1 in 4-plan, 7 in 5-execute, 6 in 6-finalize) were written without a step key and with all four context-load columns as `unmeasured`. The dispatch audit's firing comparison therefore paired 0 of the 19 finalize execution-log rows (`keyless_boundary_rows: 6`, `unpaired_execution[19]`), `context_position_cost` measured 0 of 14 rows, and the dispatch-channel confidence was graded `low` (6 finalize dispatch lines against 21 completions, 9 of 14 terminal steps with no evidence).

## Root cause

The orchestrator and the finalize dispatcher call `manage-metrics record-dispatch-boundary` without `--step-id` and without the `--input-tokens` / `--output-tokens` / `--cache-read-input-tokens` / `--cache-creation-input-tokens` figures, although `manage-metrics` SKILL.md says to forward the dispatch's step key on every call. The key-first join of `reconcile-ledgers` and the retrospective's firing comparison then fall back to timestamp windows or measure nothing.

## Proposed action

Pass `--step-id {step_id}` (the same key `record-step` writes) on every `record-dispatch-boundary` call site in the plan-marshall phase-dispatch workflow and in phase-6-finalize, and forward the four context-load totals when the runtime reports them. Add a retrospective check that grades a plan whose boundary rows are all keyless as an instrumentation finding against the dispatcher.

## Evidence

- aspect: execution-context-dispatch-audit — firing_comparison 4-plan/5-execute/6-finalize keyless_boundary_rows 1/7/6, paired_firings 0; channel_completeness confidence low
- aspect: log-analysis — context_position_cost total_rows 14, measured_rows 0; every dispatch-boundary row lists all four context-load columns as unmeasured
- aspect: logging-gap-analysis — DISPATCH_TERMINATION_CAUSE gap on keyless rows
