envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T18:20:19Z

component=plan-marshall:plan-marshall
category=bug
route=plan-marshall lessons-routing (foreign component, forward per standing rule)
confidence=high

# Forward leaf usage and step key on every execute dispatch-boundary row

## Context

In PLAN-V2-138 (pm-mcp-core) the 5-execute dispatch-boundary file holds 17 rows. Four `verification_handback` rows (07:34, 08:26, 08:58, 12:23 UTC) record `total_tokens 0`, `tool_uses 0`, `duration_ms 0`, and 14 of the 17 rows carry no `--step-id`. The dispatch audit's firing_comparison therefore pairs 0 execute rows with the 8 execution_log rows, and the 5-execute token figure falls back to the boundary sum while under-counting those four dispatches. All 41 rows across phases also leave the four context-load columns unmeasured.

## Root cause

On the hand-back path of the execute loop (plan-marshall:plan-marshall workflow/execution.md, after the leaf returns with verification_handback) the orchestrator calls `record-dispatch-boundary` without forwarding the leaf's usage figures and without a step key, at least on re-attach and resume returns.

## Proposed action

Make the execute-loop record-dispatch-boundary call forward the returned usage (total, tool uses, duration) and a step key (the envelope id or owed task) on every return, including the re-attach and resumed-session paths, and refuse a zero-usage row unless the return carried no usage tag at all (then write `unmeasured`, not `0`).

## Evidence

- aspect: logging_gap_analysis - 4 zero-token verification_handback rows, 14 keyless rows
- aspect: execution_context_dispatch_audit - firing_comparison 5-execute paired_firings 0, keyless_boundary_rows 14
- aspect: log_analysis - context_position_cost measured_rows 0 of 41
