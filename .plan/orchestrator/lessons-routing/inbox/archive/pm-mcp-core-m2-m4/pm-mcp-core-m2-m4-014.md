envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:02Z

# Candidate lesson: Keep the change ledger readable after the worktree is removed

- Component: plan-marshall:plan-retrospective
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-022 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Retrospective of plan primitive-spi-and-validators (log analysis, plan efficiency). Read from the `analyze-logs` result and the work log.

## Context

The retrospective reports build time as `unavailable`: `ledger_present: false`, `ledger_readable: false`, `ledger_rows_scanned: 0`. The plan ran 43 builds (42 Maven, 1 pyproject) that the script log shows, with 2783950 ms of cumulative Maven wrapper time. The ledger existed during the run: the work log names it at `.plan/local/worktrees/primitive-spi-and-validators/.plan/work/change-ledger.jsonl`, and the execute leaves report writing rows to it ("ledger row 72").

## Root cause

The ledger lives in the plan's worktree. The retrospective runs after the step that merges and removes the worktree, so the build-time oracle is gone before its only per-plan reader runs. The plan directory holds `build-results/` logs but no copy of the ledger.

## Evidence

- `fragment-log-analysis`: `build_time.ledger_present: false`, `total_build_seconds: unavailable`, `log_build_calls: 43`.
- Work log 78eec1 names the ledger path inside the worktree.
- The plan directory listing has no `change-ledger.jsonl`.

## Not established

Whether a fold of the ledger into the plan directory is meant to happen at merge and failed here, or does not exist. The retrospective did not look for the ledger anywhere but where the script looks.

## Proposed action

Copy or fold the ledger into the plan directory before the worktree is removed, in the same step that folds the global logs, and let `analyze-logs` name the path it looked at so "not found" and "found empty" can be told apart from the report alone.
