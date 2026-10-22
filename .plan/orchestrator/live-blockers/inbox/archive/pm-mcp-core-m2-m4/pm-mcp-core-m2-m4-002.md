envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-21T12:58:17Z

# Finding: every opencode runbook-lane landing carries `total_tokens=unknown`, so `inbox landing-check` is incomplete by construction

Source: epic `pm-mcp-core-m2-m4`, seven landings on opencode with model `deepseek-v4.1-flash`: PLAN-78 (#111), PLAN-88 (#116), PLAN-81 (#114), PLAN-90 (#120), PLAN-82 (#121), PLAN-83 (#125), PLAN-64 (#122). Related, already staged here: PLAN-LB-49 (opencode measurement), PLAN-LB-45 (runtime stamp).

## Observed by the orchestrator

- The ledger records, for each of the seven landing messages, `orchestrator inbox landing-check` returning `complete: false` with `missing_keys: [total_tokens]` (re-run today for PLAN-83 and PLAN-64). The landing facts block carries `total_tokens=unknown` and the footer states `guard: none on this harness (unenforced)`.
- The messages are otherwise well formed (all other required keys present), so the verdict is a property of the harness, not of a lane run that went wrong.

## Not observed

The cause (the harness measures no usage, or the lane has no source to read it from) is the lane's own statement; it was not checked in the harness here.

## Suggestion

Either the lane contract allows `unknown` as a complete value for a harness that cannot measure (so `landing-check` stops reporting a standing property as a missing key), or the opencode path measures it; the orchestrator keeps the watch open until one of the two.
