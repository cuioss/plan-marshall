envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:03Z

component=plan-marshall:manage-metrics
category=improvement
title=Dispatch-boundary rows are written without --step-id, so the ledgers cannot be paired
source_lesson=2026-11-18-07-006
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Dispatch-boundary rows are written without --step-id, so the ledgers cannot be paired

# Candidate lesson: every dispatch-boundary row was written without --step-id, so the ledgers cannot be paired

- Source signal: plan-retrospective, execution-context-dispatch-audit and logging-gap aspects
- Evidence: `firing_comparison` — 4-plan 1 boundary row / 0 execution rows, 5-execute 6 / 7, 6-finalize 9 / 18; keyless_boundary_rows = 16 of 16; paired_firings = 0 in every phase. All 16 rows also carry the four context-load columns as `unmeasured`.

## What happened

The orchestrator called `manage-metrics record-dispatch-boundary` after each phase dispatch, but never passed `--step-id`. The execute-log rows (`verify:module-tests`, `verify:quality-gate`, `automatic-review`, `pre-push-quality-gate`, ...) do carry their step ids. With one side keyless, the reconciliation had no join key, and the timestamp-window fallback paired nothing either. As a result 25 execution-log rows are reported unpaired, and the per-dispatch context-load cost (`context_position_cost`) has 0 measured rows across a 3.9M-token plan.

## Candidate rule

The dispatch sites in plan-marshall/workflow/execution.md and phase-6-finalize that call `record-dispatch-boundary` should forward the dispatch's step key (`--step-id`) and the four context-load figures on every call, since the manage-metrics contract states an omitted `--step-id` is correct only when the dispatch has no step. A run whose boundary rows are all keyless should be flagged as an instrumentation gap, not left as a silent zero pairing.


## Recurrence in the next plan (plan-18-leftover-fixes, inbox plan-18-leftover-fixes-015)

- Source signal: plan-retrospective, execution_context_dispatch_audit and logging_gap_analysis aspects, component plan-marshall:plan-marshall.
- Evidence: all 24 dispatch-boundary rows (1 in 4-plan, 5 in 5-execute, 18 in 6-finalize) were written without `--step-id`; the firing comparison paired 0 of 32 execution-log rows, and the ledger reconciliation fell back to timestamp windows.

Same root cause and same corrective rule: the orchestrator call sites do not forward the step key although the verb documents that it must be forwarded on every call that has a step. Add a check that flags a keyless boundary row in a phase whose execution log carries step ids.


## Recurrence in the third plan (git-worktrees-import, inbox plan-03-git-worktrees-import-018)

- Source signal: plan-retrospective, component `plan-marshall:manage-metrics`.
- Evidence: all 13 dispatch-boundary rows (1 in 4-plan, 4 in 5-execute, 8 in 6-finalize) carry no `step_id`, and the four token columns (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) are unmeasured. The firing comparison paired 0 boundary rows with the 20 execution-log rows; `context_position_cost` has 0 measured rows of 13.

Same root cause and same corrective rule: pass the step id and the token breakdown from the `<usage>` record on every `record-dispatch-boundary` call, and make the recorder refuse or warn on a keyless row.


## Recurrence in a fourth plan (git-core-incore-write-cas, inbox git-core-incore-write-cas-013)

- Source signal: plan-retrospective (execution-context-dispatch-audit, logging-gap-analysis), component `plan-marshall:plan-marshall`, confidence high.
- Evidence: every dispatch-boundary row of the plan (4-plan 1, 5-execute 4, 6-finalize 6, 11 in total) carries no step key. The firing comparison paired 0 of 11 boundary rows against the 19 execution-log rows (`keyless_boundary_rows` 1/4/6, `paired_firings` 0 in every phase) and reported every execution row (`verify:quality-gate`, `verify:module-tests`, `automatic-review`, `create-pr`, ...) as unpaired.
- The flag is optional, and an omitted flag silently writes an empty key, so nothing fails.

Same root cause and same corrective rule: the orchestrator call sites (execution.md after an execute envelope returns, and the finalize dispatcher after each step) must forward the dispatch's `record-step` step key as `--step-id`, and `record-dispatch-boundary` should warn when a phase that has execution-log rows receives a keyless row, so the gap shows at write time and not at retrospective time.


## Recurrence in a fifth plan (plan-05-git-core-merge-read-notes, inbox plan-05-git-core-merge-read-notes-011)

- Source signal: retrospective execution-context dispatch audit (`firing_comparison`, `dispatch_coverage`, `channel_completeness`).
- Evidence: all 18 dispatch-boundary rows are keyless (1 in 4-plan, 6 in 5-execute, 11 in 6-finalize); `paired_firings: 0` in every phase against 20 `execution_log` rows; 8 of the 10 terminal finalize steps (automatic-review, branch-cleanup, ci-verify, create-pr, sync-baseline, pre-push-quality-gate, push, sonar-roundtrip) have no token or dispatch evidence; channel confidence `low` (6 finalize dispatch lines against 20 completions); every row lists the four token-split columns as unmeasured (`context_position_cost.measured_rows: 0 of 18`). The finalize boundary total, 1.54M tokens, is the largest phase and cannot be attributed per step.

Same root cause and same corrective rule: add and persist `--step-id` on `record-dispatch-boundary` and pass it from every phase-5 verify dispatch and phase-6 step dispatch site, so `check-dispatch-audit` can pair firings and attribute the finalize spend per step.


## Recurrence in a later plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-024)

- Source signal: plan-retrospective (execution-context-dispatch-audit and log-analysis aspects). All 22 dispatch-boundary rows (4-plan 1, 5-execute 7, 6-finalize 14) carry no `step_id` and leave the input, output and cache token columns unmeasured: the firing comparison paired 0 of 34 execution-log rows, context-position cost is measured on 0 of 22 rows, finalize channel confidence is low (6 dispatch lines against 20 completions), and with three re-fires per finalize step the per-step cost of a re-fire cannot be read.
- Same root cause: the `record-dispatch-boundary` call sites pass the total tokens and the termination cause only. Pass `step_id` (finalize step or envelope id) and the token sub-columns from the leaf's `<usage>` block, and emit the `[DISPATCH]` line for every finalize dispatch.


## Recurrence in a third plan (plan-12-forms-kinds-schema-layout, inbox plan-12-forms-kinds-schema-layout-002)

- Source signal: plan-retrospective (plan_efficiency, logging_gap and log_analysis aspects). The 5-execute dispatch-boundary file holds a placeholder row `clean_exit_queue_empty 0 0 0`, recorded 12 seconds before the real row for the same envelope (335,287 tokens, 140 tool uses), and an execute row first written as an estimate and corrected later; the append-only file leaves no trace of the correction. The two measures of the 5-execute phase disagree by a factor of 1.9 (`total_tokens` over 7 closes 1,756,491, the boundary sum over 11 rows 3,368,153) and the report silently takes the larger, so the plan total (9,325,248) rests on a cell whose true value is not decidable. All 43 boundary rows leave input, output and cache tokens unmeasured, and billing is measured on 0 of 6 phases.
- Further rules on the same root cause: `record-dispatch-boundary` refuses a row with total_tokens, tool_uses and duration_ms all 0 unless a `--measured-zero` flag says it is real; it gains a supersede operation that marks a row replaced and keeps both, so a correction is auditable; and when the competing measures of one phase differ by more than a set ratio (say 1.5x) `metrics.md` and the retrospective carry a warning, not only the "largest wins" note.


## Recurrence in a later plan (plan-11-store-anchoring-signed and plan-20-leftover-fixes-2, inbox plan-11-store-anchoring-signed-011, plan-20-leftover-fixes-2-020)

Two more plans with keyless rows only. plan-11: 28 dispatch-boundary rows (1 in 4-plan, 4 in 5-execute, 23 in 6-finalize), none with a step_id, so the dispatch audit paired 0 firings against 43 `execution_log` rows and the finalize channel ratio was 7/31 (confidence low); 5 of 10 terminal finalize steps (branch-cleanup, ci-verify, finalize-step-sync-baseline, pre-push-quality-gate, push) left no token record and no `[DISPATCH]` line, so they cannot be told apart from dispatched steps whose usage was not captured. plan-20: 24 rows (1 in 4-plan, 7 in 5-execute, 16 in 6-finalize), all keyless and with the four token-split columns unmeasured; 0 of 20 finalize `execution_log` rows paired; the finalize boundary rows add up to about 2.69M tokens while `metrics.md` reports 6-finalize as `unknown`, and nobody can tell which steps spent it or how much of it was the 427K retryable `blocked_session_restart` spend. Rule: every finalize and execute dispatch site passes its `step_id` (or task number) to `record-dispatch-boundary`, inline finalize steps write an explicit zero-token record, and the recorder refuses or warns on a keyless row from a known step-dispatching role.
