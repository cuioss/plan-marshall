envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:10Z

component=plan-marshall:plan-retrospective
category=bug

# Read the change-ledger after worktree removal instead of reporting it absent

Source: plan-retrospective of plan-70-plan-instance-alignment (aspects log-analysis, plan-efficiency).

## Context

At order 995, after branch-cleanup removed the plan worktree, `analyze-logs` reported `build_time` with `ledger_present: false`, `ledger_readable: false`, `ledger_rows_scanned: 0` and `total_build_seconds: unavailable`, although the plan logged 93 build calls and its execute leaves wrote change-ledger rows during the run (Step 12a matched ledger row 179; each deliverable commit carried a `kind=change` ledger entry). The plan-efficiency aspect therefore had no build-time oracle for a plan whose builds owned 60% of script time.

## Root cause

The ledger read appears to resolve against a location that did not survive the worktree removal (or the rows were not carried to the main-checkout plan directory at integrate time), so the post-merge retrospective sees no ledger.

## Proposed action

Have the integrate/branch-cleanup step carry the plan's change-ledger rows into the main-checkout plan directory (or have `summarize_build_ledger` resolve the main-anchored store), and add a test that a retrospective run after worktree removal reads a non-zero `ledger_rows_scanned` for a plan that wrote ledger rows.

## Evidence

- log-analysis: build_time ledger_present false, log_build_calls 93, build_count_reconciliation ledger_available false
- plan-efficiency: total_build_seconds unavailable
- chat-history-analysis: Step 11c leaf "Change-ledger row 179 ... matches the current tree"
