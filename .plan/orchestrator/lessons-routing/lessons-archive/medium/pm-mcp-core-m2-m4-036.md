envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T20:00:35Z

# Scope module_mapping temp file per plan so concurrent plans do not collide

**Component**: `plan-marshall:phase-2-refine` (module-mapping step)
**Category**: bug
**Confidence**: high
**Signal source**: plan-retrospective (chat history, logging gaps), plan-38-review-bot-re-review

## Context

During phase 2-refine, the refine leaf wrote its module mapping to `.plan/temp/module_mapping.toon`. That name is shared by every plan. While this plan was running, a concurrent plan in the same checkout wrote the same file, so this plan's mapping was replaced mid-run. Refine recovered only because it had already copied its mapping to the plan-local `work/module_mapping.toon` and read that copy back.

## Root cause

The temp path is not scoped to a plan. Two plans that refine at the same time race on one file, and the last writer wins.

## Proposed action

Scope the temp path by plan id (for example `.plan/temp/{plan_id}/module_mapping.toon`), or write straight to the plan-local `work/` through `manage-files`. Then check the other phase workflows for fixed `.plan/temp/` names that have the same race.

## Evidence

- chat_history_analysis: the refine hand-back says "`.plan/temp/module_mapping.toon` was overwritten mid-run by another plan, because the file name is shared"
- logging_gap_analysis: the collision appears only in the hand-back. work.log has no line for it.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-38-review-bot-re-review-004.md` from plan plan-38-review-bot-re-review (PLAN-38, #24)
