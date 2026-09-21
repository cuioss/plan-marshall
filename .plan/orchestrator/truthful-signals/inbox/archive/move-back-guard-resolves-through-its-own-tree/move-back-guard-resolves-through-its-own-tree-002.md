envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:48:41Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=move-back-guard-resolves-through-its-own-tree
source_pr=1361

# 6-finalize is instrumented by nothing and reports as a blank row everywhere

## Context

On this plan, `6-finalize` ran 15 recorded steps — three of them re-firing to `firing_count: 3` after two loop-back rounds — plus a 1102-second merge-queue wait and three `ci_complete_precondition` calls of roughly 9.5 minutes each. The `tools-integration-ci` script alone accumulated 4,972,700 ms across 38 calls, and `build-server` a further 4,913,110 ms across 46.

Every ledger reports that phase as empty:

- `work/metrics.toon` `[6-finalize]` carries `start_time` and nothing else — no `end_time`, no `total_tokens`, no `tool_uses`.
- No `work/metrics-accumulator-6-finalize.toon` exists, so `generate` had nothing to fold.
- No `work/metrics-dispatch-boundaries-6-finalize.toon` exists, so the `DISPATCH_TERMINATION_CAUSE` rule is precondition-skipped and audits nothing.
- `execution.toon`'s `execution_log` holds 8 rows, **all** from `5-execute` and **zero** from `6-finalize`, even though its writer explicitly accepts that phase.

The consequence is arithmetic, not cosmetic. `metrics.md` reports `4,135,501 (n=4/6)` tokens against a `multi_module + bug_fix` **error** anchor of 2.0M. The anchor was crossed by more than 2x on a figure that excludes the entire finalize phase.

## Root cause

`accumulate-agent-usage` and `record-dispatch-boundary` are called by the finalize dispatcher only for steps that run as dispatched `execution-context` leaves. Many finalize steps on this run executed **inline in the orchestrator context**, which produces no `<usage>` envelope and therefore no accumulator write and no boundary row. The instrumentation is keyed on the execution shape rather than on the step boundary, so a step that ran inline is indistinguishable from a step that never ran.

`record-step` has no such excuse — its writer accepts `6-finalize` — yet not one finalize step recorded a row.

## Proposed action

1. Make the finalize step boundary itself the instrumentation point: have `mark-step-done` (or the dispatcher wrapper around it) always emit a `record-step` row for the step, dispatched or inline, so `execution_log` covers the phase it declares it covers.
2. For inline steps, record the boundary with the context-load columns written as the literal `unmeasured` — the mechanism `record-dispatch-boundary` already uses for its four context-load columns — rather than writing nothing. "Ran inline, spend not measurable here" is a different fact from "did not run", and only the first is true.
3. Have `metrics.md` mark a Total whose denominator excludes the terminal phase more loudly than the current `(n=4/6)` marker, since a floor that omits the largest phase is not usefully comparable to a complete one.

## Evidence

- aspect: plan_efficiency — `totals_tokens 4135501`, `totals_tokens_population_count 4` of denominator `6`; `phases_missing_end_time: [6-finalize]`
- aspect: logging_gap_analysis — gap rows for `phase-6-finalize` under both `DISPATCH_TERMINATION_CAUSE` and `OUTCOME_COVERAGE`
- `manage-metrics reconcile-ledgers` — `union_rows: 9`, `execution_log_rows: 8`, `boundary_rows: 1`, with the single boundary row belonging to `4-plan`
- aspect: execution_context_dispatch_audit — `dispatch_coverage`: 0 dispatched / 0 inline / **15 no_evidence** of 15 finalize steps
