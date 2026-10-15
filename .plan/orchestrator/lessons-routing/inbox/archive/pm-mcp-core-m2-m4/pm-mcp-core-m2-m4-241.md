envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:58Z

# Record Maven build runs as change-ledger build rows so build time is measured

**Source plan:** plan-21-entity-addressing (PR #54, merged b25d115)
**Signal source:** plan-retrospective (aspects log-analysis, plan-efficiency, logging-gap-analysis)
**Suggested component:** plan-marshall:manage-change-ledger (writer side: plan-marshall:build-maven build wrapper)
**Category:** bug
**Confidence:** high

## Context

plan-21 ran 27 `plan-marshall:build-maven:maven` calls, which owned 4705 s of script time (48.8% of all script time, the largest single cost). The change-ledger was present and readable (7 rows scanned) but held no build row for this plan, so the build-time oracle reports `total_build_seconds: unavailable` and `build_count: 0`, and the log-vs-ledger build-count reconciliation could not run.

## Root cause

Maven builds in this (non-marketplace, Maven) project are not appended to the change-ledger as build rows; the ledger only carries the other row kinds. Every build ran in-process (build server disabled, `in_process_fallback`), which may be the path that skips the ledger write.

## Proposed action

Make the build wrapper write one ledger build row (command, duration_seconds, status) per run on the in-process path as well, or document the gap and have `analyze-logs` fall back to the script-execution log with an explicit "log-derived, not ledger" label.

## Evidence

- aspect: log-analysis: `build_time.ledger_rows_scanned: 7`, `summed_rows: 0`, `log_build_calls: 27`, `ledger_unavailable_reason: the change-ledger holds no row for this plan`
- aspect: log-analysis: script_cost_rollup ranks build-maven first (27 calls, 4705010 ms)
- work.log: every build logs `[BUILD-SERVER] resolved build (requested=auto, resolved=in_process, reason=disabled, mechanism=in_process_fallback)`

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-008.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
