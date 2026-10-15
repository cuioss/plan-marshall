envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T13:50:25Z

# Candidate lesson: a cross-module log-record change was left untested by the module_testing task

- Source: Q-Gate finding 92f143 (phase 4-plan, module_mapping_validator, resolution fixed)
- Plan: session-log-and-generations (PR #51)
- Signal: signal_qgate_pending_count
- File: pm-core/src/main/java/de/planmarshall/core/log/PmMcpLogMessages.java

## Observation

Implementation task 9 (deliverable 5) changed pm-core `PmMcpLogMessages` to add new
log records, while its sibling module_testing task 10 targeted only pm-runtime test
files. No test pinned the new records; `PmMcpLogMessagesTest` checks ranges and
uniqueness only and ran only through the `-am` build. `doc/developer/test-impl-mapping.adoc`
does not exist in this repository, so no mapping row could justify the cross-module routing.

## Resolution in run

Operator decision: TASK-10 gained a step that extends `PmMcpLogMessagesTest` with a
template pin for each new record.

## Possible lesson

When a deliverable adds `LogRecord` constants to `PmMcpLogMessages` in pm-core from a
plan whose main code is in another module, task planning should add a pm-core test step
that pins each new record's template. The split by module should not leave the log
records with no test. Owning component is likely plan-marshall:phase-4-plan (task
derivation), or a project-level planning convention for pm-mcp-core.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `session-log-and-generations-002.md` from plan session-log-and-generations (PLAN-12, #51; Claude Code)
