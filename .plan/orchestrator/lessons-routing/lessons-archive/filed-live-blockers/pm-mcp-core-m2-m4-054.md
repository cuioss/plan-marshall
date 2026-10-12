envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:15Z

# Align fix-task deliverable 0 in triage with what manage-tasks commit-add accepts

## Context

The finalize-feedback triage (verification-feedback workflow) says fix tasks are filed under
deliverable 0. In PLAN-06 `manage-tasks commit-add` rejected deliverable 0 as a missing field in all
three triage runs (round 1, its re-run after the operator answers, round 2). Each leaf worked around
it by picking "the closest owning deliverable" (5, 7, 8, 11) - TASK-32 was filed under deliverable 8
while it edits deliverable-7 files, and TASK-31 (documentation) under 11.

## Root cause

The workflow text and the commit-add validator disagree on whether 0 is a valid deliverable number,
so every leaf improvises and fix tasks get attributed to deliverables they do not belong to.

## Proposed action

Pick one contract: either commit-add accepts deliverable 0 for fix tasks (origin finding/sonar), or
the workflow names the rule for choosing a real deliverable. Add a test that the workflow's
documented fix-task shape passes commit-add.

## Evidence

- aspect: chat_history_analysis - three triage leaves: "the workflow says fix tasks use deliverable 0, but commit-add rejects 0 as a missing field"
- aspect: request_result_alignment - fix tasks TASK-22..33 attributed to deliverables 5, 7, 8, 11

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-06-store-substrate-012.md` from plan plan-06-store-substrate (PLAN-06, #26)
