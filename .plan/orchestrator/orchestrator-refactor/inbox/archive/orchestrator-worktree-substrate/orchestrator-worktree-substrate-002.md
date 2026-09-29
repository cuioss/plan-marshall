envelope_version=1
sender_type=plan
sender_id=orchestrator-worktree-substrate
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-28T19:16:51Z

component=plan-marshall:manage-metrics
category=bug

# Stamp step_id and token figures on every dispatch-boundary row

## Context

In orchestrator-worktree-substrate, all 35 dispatch-boundary rows (1 in 4-plan, 11 in 5-execute, 23 in 6-finalize) carry no `step_id`. All 11 execute rows record `total_tokens=0`, `tool_uses=0` and `duration_ms=0`, and every finalize `record-step` row records `total_tokens=unmeasured`. `check-dispatch-audit`'s `firing_comparison` therefore paired 0 of 63 execution rows, and `context_position_cost` shows 35 of 35 rows unmeasured.

## Root cause

The dispatchers call `record-dispatch-boundary` without `--step-id` and without the per-dispatch usage figures. The execute path records nothing at all, and the finalize path records usage on the boundary row but not on the matching `record-step` row. The two ledgers can then only be joined by timestamp window, and here that join did not pair any rows.

## Proposed action

In the phase-5-execute and phase-6-finalize dispatchers, forward the active step key as `--step-id` and pass the leaf's usage figures on every `record-dispatch-boundary` call. Add a regression test asserting that a dispatched finalize step yields one boundary row and one `record-step` row sharing a key.

## Evidence

- aspect: execution_context_dispatch_audit - firing_comparison paired_firings 0 in every phase; keyless_boundary_rows 35
- aspect: logging_gap_analysis - 11 execute boundary rows at zero tokens
- aspect: llm_to_script_opportunities - step_id derivation belongs in the dispatcher script, not the LLM
