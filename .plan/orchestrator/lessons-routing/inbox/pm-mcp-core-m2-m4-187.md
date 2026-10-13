envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:20Z

# Candidate lesson: write a change-ledger build row for every maven build run

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:build-maven` / `plan-marshall:manage-change-ledger`. Category: bug. Confidence: medium.

## Context

The plan's script log shows 42 `plan-marshall:build-maven:maven` calls, about 49% of all script time (6090 s). The change-ledger was present and readable, with 7 rows scanned, but held no build row for this plan. So `log-analysis` reports `total_build_seconds: unavailable`, the build-count reconciliation is unmeasured, and the efficiency aspect cannot state build time.

## Root cause

Either the maven wrapper does not write `kind=build` ledger rows in this project, or it writes them where the plan-scoped reader does not look (for example the worktree copy that was removed).

## Proposed action

Check that every `maven run` appends a build row (command, duration, status) to the plan's change-ledger, and that the row survives worktree removal. Add a test for that case.

## Evidence

- aspect: log-analysis — `log_build_calls: 42`, `build_time.ledger_rows_scanned: 7`, `summed_rows: 0`, "the change-ledger holds no row for this plan"
- aspect: plan-efficiency — `total_build_seconds: unavailable`

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-022.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
