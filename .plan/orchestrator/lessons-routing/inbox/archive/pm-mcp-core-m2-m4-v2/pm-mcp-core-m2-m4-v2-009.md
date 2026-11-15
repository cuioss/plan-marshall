envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T23:11:02Z

component=plan-marshall:phase-5-execute
category=bug
title=Record ledger rows for the quality-gate rewrite commit before the 5-6 move
confidence=high

# Record ledger rows for the quality-gate rewrite commit before the 5-6 move

## Context

In plan-v2-57-default-plan-lanes-and-run, phase 5 handed the whole-module verify back to the orchestrator. The `verify -Ppre-commit` gate rewrote two test files (DefaultPlanUnitTest.java of D2, DefaultPlanRunTest.java of D3) and the rewrite was committed as c6c1767f. That commit carried no `kind=change` change-ledger row, so the re-dispatched execute leaf's `manage-status transition --completed 5-execute` was refused with `execute_commits_unrecorded` (signature `bookkeeping_gap`).

## Root cause

The quality-gate rewrite commit path writes no ledger row, while the transition guard requires one per branch commit. A single `append` can name only one deliverable, and the rewrite commit spanned two.

## Proposed action

Have the commit path of the orchestrator-tier `verify:quality-gate` hand-back append its own `kind=change` rows, one per deliverable, mapping each rewritten path to its deliverable through the task step targets. Alternatively, let `append` accept a multi-deliverable commit. Either way, the 5->6 move should not need an operator decision for a mechanical rewrite.

## Evidence

- script_failure_analysis: manage-status transition exit 1 at 2026-11-11T15:29:59Z (execute_commits_unrecorded, 1 of 6 commits unrecorded)
- logging_gap_analysis: 5-execute dispatch boundary row with termination_cause=error, 136153 tokens
- chat_history_analysis: the execute leaf returned status error and asked the operator how to attribute the two-deliverable commit
