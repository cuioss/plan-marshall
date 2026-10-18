envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:34Z

component=plan-marshall:manage-tasks
category=bug
confidence=medium
source=plan-retrospective (chat-history-analysis); finalize triage hand-back for PR #90 (TASK-27/28)

# Accept deliverable 0 for origin fix tasks created by finalize triage

## Context

The finalize triage of PR #90 created fix tasks for bot findings that belong to no single deliverable (TASK-27 review defects across several classes, TASK-28 the Sonar clean-up). `manage-tasks` rejected `deliverable: 0` with `origin: fix` ("missing required field: deliverable") through both `commit-add` and `batch-add`, so both tasks were attached to deliverable 7, and a failed `commit-add` left a stale `work/pending-tasks/triage-a.toon`.

## Root cause

The task schema treats deliverable 0 as absent, although a finalize fix task that spans deliverables has no truthful deliverable index.

## Proposed action

Accept `deliverable: 0` (or an explicit cross-deliverable marker) for `origin: fix` tasks, and clean up the pending-task scratch file when `commit-add` fails.

## Evidence

- triage hand-back: "`deliverable: 0` with `origin: fix` is rejected by this manage-tasks version ... so both tasks use deliverable 7. A stale scratch file is left at work/pending-tasks/triage-a.toon"
