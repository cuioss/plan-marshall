envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:04:17Z

component=plan-marshall:phase-5-execute
category=improvement
title=Emit OUTCOME lines for tasks completed before the OUTCOME guard landed

# Emit OUTCOME lines for tasks completed before the OUTCOME guard landed

## Context

In plan close-the-leftover-gate-gaps, 5 tasks reached done but work.log carries only 2 [OUTCOME] (plan-marshall:phase-5-execute) Completed lines (TASK-004, TASK-005 — both triage-added fix tasks). TASK-001..003 completed with no OUTCOME line, so OUTCOME_COVERAGE reads 2 of 5.

## Root cause

OUTCOME emission began mid-plan: the early tasks ran before the script-level OUTCOME guard existed in the executing build, and nothing re-emitted their completion once the guard landed.

## Proposed action

When the OUTCOME guard is introduced (or on re-entry), backfill one OUTCOME line per already-done task, or re-emit completion for tasks whose done-transition predates the guard — so coverage is measured over the whole task population, not only the post-guard tail.

## Evidence

- aspect: logging_gap_analysis — 5 tasks done but only 2 [OUTCOME] lines (TASK-004, TASK-005)
- aspect: log_analysis — phase5 outcome_for_diffed_tasks names TASK-001..003 with diff but no outcome
