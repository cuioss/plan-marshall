envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:13Z

component=plan-marshall:build-server-client
category=improvement
title=Log a configured-disabled build server at INFO, not WARNING
source_lesson=2026-11-18-18-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Log a configured-disabled build server at INFO, not WARNING

# Candidate lesson: a build server that is configured off is logged at WARNING on every build

- Source signal: plan-retrospective of plan git-worktrees-import (inbox plan-03-git-worktrees-import-019), component `plan-marshall:build-server-client`, confidence high.

## What happened

Each of the 26 Maven builds of the plan wrote the same work-log line at WARNING: `[BUILD-SERVER] resolved build (requested=auto, resolved=in_process, reason=disabled, ... mechanism=in_process_fallback, serialization=fallback-slot)`. These are all 27 work-log warnings of the plan, so the warning channel carried no other signal.

## Root cause

The resolver logs the in-process fallback at WARNING whatever its reason, including `reason=disabled`, which is the expected, configured state of a project that has not enrolled in the build server.

## Candidate rule

Log `reason=disabled` (not enrolled, or switched off by configuration) at INFO, or once per plan, and keep WARNING for fallbacks the operator did not choose (daemon unreachable, stale identity, enrolment mismatch).


## Recurrence in the next plan (git-worktrees-hardening, inbox plan-19-git-worktrees-hardening-013)

- Source signal: plan-retrospective (logging-gap-analysis, log-analysis), work log hash 16697f, confidence high.
- All 36 Maven builds of the plan logged the same `[BUILD-SERVER] ... reason=disabled ... mechanism=in_process_fallback` line at WARNING: 36 of the plan's 37 work-log warnings.

Same root cause and same rule: log the `reason=disabled` fallback at INFO, or at WARNING once per plan, and keep WARNING for unexpected fallbacks (daemon unreachable, enrolment mismatch).
