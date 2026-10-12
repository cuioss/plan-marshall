envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:09Z

# Candidate lesson: the execute phase-complete line reports the tasks of one entry against the plan total and reads as if most tasks were open

- Component: plan-marshall:phase-5-execute
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-08-006 (created 2026-10-10), epic pm-mcp-core-m2-m4

Source: retrospective of the plan (aspects logging gaps, chat history). Verified against the work log.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.
Proposed component: `plan-marshall:phase-5-execute`. Proposed category: improvement.

## Context

Each time the execute phase ended, it wrote one summary line to the work log:

- `04a40d` (2026-10-09T23:00:16Z): "Execute phase complete — 2/6 tasks done"
- `dcf6a9` (2026-10-09T23:33:31Z): "Execute phase complete — 1/7 tasks done"
- `020ed0` (2026-10-10T06:36:00Z): "Execute phase complete — 1/8 tasks done"

At each of these moments every task of the plan was done (6 of 6, 7 of 7, 8 of 8). The first number is the count of tasks the last entry into the phase completed; the second is the plan total.

## Root cause

The line divides a per-entry numerator by a plan-wide denominator. The phase is entered several times on any plan of some size (six entries here: two for unmeasured build commands, one at a budget boundary, two after review fixes), so the two numbers describe different populations on almost every run.

## Consequence

A reader of the log, or a script that parses the line, sees a phase that completed with most tasks open. The hand-off that ran TASK-007 pointed this out in its report ("Phase-complete log line says 1/7 tasks done. It counts this entry's one task against the plan's seven; all seven are done.").

## Proposed action

Write the plan-wide count in the line, and name the per-entry count separately if it is wanted, for example "8/8 tasks done (1 in this entry)".

## Evidence

- aspect logging_gap_analysis: the three work-log lines above; task outcome coverage is otherwise complete (8 of 8 outcome lines).
- aspect chat_history_analysis: the hand-off report after TASK-007 names the line as misleading.

Classification is left to the pickup.
