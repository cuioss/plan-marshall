envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:14Z

# Candidate lesson: Make scope_creep_check persist a finding type the findings store accepts

- Component: plan-marshall:phase-5-execute
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-14-011 (created 2026-10-10), epic pm-mcp-core-m2-m4

- component: plan-marshall:phase-5-execute
- category: bug
- confidence: high
- source plan: lock-manager-and-leases

## Context

`plan-marshall:phase-5-execute:scope_creep_check check` failed with exit 1 on all three runs of this plan (06:38, 08:25, 09:33 on 2026-10-10). Each time it tried to persist a finding of type `scope_creep_warning`, and `manage-findings` rejected the type ("Invalid finding type: scope_creep_warning. Must be one of bug, improvement, ..."). On the first run the execute dispatch held the 5-execute -> 6-finalize transition and returned `finding_persist_failed`, which cost an extra orchestrator round and recorded a productive 241K-token dispatch as `error`.

A second defect rides with it: the check diffs from `plan_creation_sha`. After the branch was rebased onto main (PRs #18, #19, #21), the residual set grew to 59 and then 33 files that came from upstream, not from the plan.

## Root cause

The finding type the check emits is not in the findings store's type enum, and the comparison base is not moved when the branch absorbs main.

## Proposed action

Emit an accepted type (or add `scope_creep_warning` to the enum in one change with the check), add a test that persists the check's real finding through the store, and diff from the merge base with the current base branch instead of `plan_creation_sha`.

## Evidence

- aspect: script_failure_analysis — 3 occurrences, script_internal_error in plan-marshall:phase-5-execute:scope_creep_check
- aspect: logging_gap_analysis — the 06:39 5-execute dispatch row is `error` (240983 tokens) although TASK-015 completed
- aspect: chat_history_analysis — every later execute report names it as a known tooling defect and continues


## Recurrence

The same plan also filed this as `lock-manager-and-leases-001.md` (three occurrences, ERROR 5b10d1 and 1b0cce), folded here.

Source: inbox `lock-manager-and-leases-015.md`, plan lock-manager-and-leases (PLAN-01, #20).
