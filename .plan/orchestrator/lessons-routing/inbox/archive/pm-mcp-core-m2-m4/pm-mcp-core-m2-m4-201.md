envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:55Z

# Log the disabled build-server fallback at INFO, not WARNING

Component: `plan-marshall:build-server-client` · Category: improvement · Source: plan-retrospective of `static-verifier-rule-gaps-completion`

## Context

Every Maven build of this plan wrote `[WARNING] [BUILD-SERVER] resolved build (requested=auto, resolved=in_process, reason=disabled, mechanism=in_process_fallback, serialization=fallback-slot)` to work.log. That line accounts for 35 of the 41 work-log warnings. The build server is disabled by configuration in this project, so in-process is the expected path, not a degradation.

## Root cause

The resolver logs the fallback at WARNING whatever the reason, so `reason=disabled` (configured) and a real fallback (daemon unreachable, enrolment missing) look alike. The real warnings of the plan, such as the TASK-12 BLOCKED entry and the pre-push footprint note, are buried among them.

## Proposed action

Log at INFO when `reason=disabled` (or any operator-configured opt-out). Keep WARNING for unplanned fallbacks such as an unreachable daemon or a failed preflight. Consider logging the disabled state once per plan instead of once per build.

## Evidence

- aspect: logging-gap-analysis — 35 identical BUILD-SERVER warnings, one per build
- aspect: log-analysis — warnings_work 41, log_build_calls 38

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-012.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
