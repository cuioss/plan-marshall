envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:12Z

# Candidate lesson: log a build server that is disabled by configuration at INFO, not WARNING, on every build

Source: plan-retrospective of plan-04-service-unit (aspects log-analysis, logging-gap-analysis). Not covered by the 10 lessons-capture messages.

## Context

Every Maven build in this plan wrote one work-log line at WARNING level: `[BUILD-SERVER] resolved build (requested=auto, resolved=in_process, reason=disabled, ... mechanism=in_process_fallback, serialization=fallback-slot)`. That accounts for about 28 of the 31 work-log warnings. The build server is disabled by configuration in this project, so the in-process build is the expected path, not a degradation.

## Root cause

The build-resolution log line does not separate "disabled by configuration, as expected" from "fell back because the server was unavailable". Both are logged at WARNING.

## Proposed action

Log `reason=disabled` (configured off) at INFO, or once per plan. Keep WARNING for genuine fallbacks such as an unreachable daemon or an unenrolled project when enrolment was expected. Then `warnings_work` in log-analysis counts real warnings again.

## Evidence

- log-analysis: `warnings_work: 31`, `log_build_calls: 28`
- work.log: one `[WARNING] [e04bde] [BUILD-SERVER] ... reason=disabled` line per build, from TASK-1 to the last pre-push gate

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-012.md` from plan plan-04-service-unit (PLAN-04, #25)
