envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T17:24:46Z

component=plan-marshall:phase-5-execute
category=bug
bundle=plan-marshall
created=2026-07-28

# Per-task [ARTIFACT] log emission is missing for most completed tasks

## Context

The logging-gap-analysis retrospective aspect found that 8 of 8 `[OUTCOME] (phase-5-execute)
Completed TASK-NNN` entries in this plan correspond to a task with a non-empty diff (TASK-001
alone wrote 8 production files across 8 skills), but only TASK-008 (a single-file test addition
added via a loop-back) is followed by a matching `[ARTIFACT] (plan-marshall:phase-5-execute:{N})`
log line. TASK-001 through TASK-007 — the bulk of this plan's actual production-code and test
changes — produced file diffs with zero per-task `[ARTIFACT]` emission.

## Root cause

Not diagnosed from this plan's evidence alone: unclear whether `[ARTIFACT]` emission is gated
on a code path only TASK-008's loop-back re-entry happened to exercise, or whether normal
task-completion in the primary (non-loop-back) execute pass simply omits the per-task artifact
line that the expected-log-pattern contract (`logging-gap-analysis.md` § Expected Log Patterns)
requires.

## Proposed action

Audit `phase-5-execute`'s task-completion path (the code/workflow step that logs `[OUTCOME]
Completed TASK-NNN`) for the sibling `[ARTIFACT] (phase-5-execute:{N})` emission call, confirm
whether it is present-but-conditional or simply absent on the primary completion path, and add
it unconditionally whenever a completed task's diff against `task_start_sha` is non-empty — the
same rule TASK-008's loop-back path apparently already satisfies.

## Evidence

- aspect: logging-gap-analysis — ARTIFACT_EMISSION finding (severity: error), full plan:
  unchecked-finding-persist-loses-the-finding, PR #1038
- aspect: execution-context-dispatch-audit — same plan's dispatch-coverage findings show a
  parallel "only the re-entrant/last invocation gets full log evidence" shape, suggesting a
  possibly-shared root cause across two different logging obligations
