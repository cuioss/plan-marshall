envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T23:11:04Z

component=plan-marshall:phase-5-execute
category=bug
title=Diff each task against its own start, not the envelope base
confidence=medium

# Diff each task against its own start, not the envelope base

## Context

All 6 tasks of plan-v2-57-default-plan-lanes-and-run ran in one execute envelope. Each task's `[ARTIFACT] (plan-marshall:phase-5-execute:N)` lines and its `changed_files` list are cumulative. TASK-001 (D1, fixtures only) lists `WorkflowEngine.java`, the D5 spec and engine docs and ADR 015, and every later task repeats the whole growing set (TASK-006 lists 15 files). TASK-001's `task_start_sha` is the main head 42674607, the base of the whole envelope.

## Root cause

The per-task diff that feeds the artifact lines uses a start SHA shared by the envelope instead of the previous task's completion commit, so the attribution grows monotonically. The retrospective's ARTIFACT_EMISSION check passes 6/6 while the lists do not say which task wrote which file.

## Proposed action

Stamp `task_start_sha` when each task starts (or diff against the previous task's commit) so `changed_files` and the `[ARTIFACT]` lines are per task. Add a test where two tasks in one envelope touch disjoint files.

## Evidence

- logging_gap_analysis: work.log lines 125-219, cumulative artifact lists per task
- artifact_consistency / tasks/TASK-001.json: changed_files holds 9 paths, including D5 production files
