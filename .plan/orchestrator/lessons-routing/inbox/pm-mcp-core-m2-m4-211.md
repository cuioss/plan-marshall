envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:53Z

# Write a change-ledger build row for every Maven run, including the in-process fallback

## Context

Plan diagram-generator logged 20 `plan-marshall:build-maven:maven` calls (53% of all script time, 2899s cumulative). The change-ledger for the plan was present and readable (7 rows), but held 0 build rows. So the retrospective's build-time oracle reports `total_build_seconds: unavailable`, and the build-count reconciliation cannot render a verdict. Every Maven run resolved through the build server's `in_process_fallback` (reason=disabled).

## Root cause

Not confirmed. Either the in-process fallback path of the Maven wrapper skips the ledger write, or the Maven wrapper never writes build rows. Either way the build-time oracle is blind for this repository.

## Proposed action

Check where build rows are written. Make sure the Maven run path, including `in_process_fallback`, appends one build row (command, status, duration_seconds) per run. Add a test that one in-process Maven run produces exactly one ledger build row.

## Evidence

- log-analysis: build_time ledger_rows_scanned 7, summed_rows 0, build_count 0; log_build_calls 20; ledger_unavailable_reason "the change-ledger holds no row for this plan"
- plan-efficiency: total_build_seconds unavailable despite 20 builds
- work.log: every build logged `[BUILD-SERVER] resolved build (requested=auto, resolved=in_process, reason=disabled, mechanism=in_process_fallback)`

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-010.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
