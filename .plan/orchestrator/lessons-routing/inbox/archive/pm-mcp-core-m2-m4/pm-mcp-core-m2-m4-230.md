envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T13:50:29Z

# Candidate lesson: the triage fix-task shape "deliverable: 0" is rejected by manage-tasks commit-add

- Source: dispatcher observation (in-run; occurred twice this run). Script-failure signal
  not scanned by the dispatcher, so this cluster is unverified against the work log.
- Plan: session-log-and-generations (PR #51)

## Observation

The triage workflow's fix-task shape sets `deliverable: 0` for the fix tasks it creates
from review findings (here TASK-15 and TASK-16 for CodeRabbit comments). `manage-tasks
commit-add` rejected that shape both times, so the documented triage flow produces an
input that the task store it feeds will not accept.

## Possible lesson

The triage workflow's fix-task template and the `manage-tasks` validator must agree on
how a fix task that belongs to no deliverable is shaped: either `commit-add` accepts the
sentinel deliverable 0, or the triage template uses the shape the validator expects.
Add a test that feeds the triage template's exact output to `commit-add`. Candidate
owners: plan-marshall:manage-tasks and the triage workflow of plan-marshall:plan-marshall.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `session-log-and-generations-007.md` from plan session-log-and-generations (PLAN-12, #51; Claude Code)
