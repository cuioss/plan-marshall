envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:26Z

component=plan-marshall:phase-5-execute
category=bug
confidence=medium
source_plan=every-module-counts-and-the-campaign-can-finish
recurrence_of=2026-05-08-14-001

# Emit [OUTCOME] for every completed task, including ones that complete late in a dispatch

## Context

13 tasks reached `status: done`, but `work.log` carries only 11 `[OUTCOME] (plan-marshall:phase-5-execute) Completed` lines. TASK-008 and TASK-011 are unpaired, and the fact extractor separately confirms both produced a non-empty diff (`tasks_with_diff_no_outcome: [TASK-008, TASK-011]`). Two tasks that changed files completed without announcing it.

## Root cause

Not established from the offline record. The plan ran 6 dispatch clusters across 8 recorded 5-execute terminations, including one `error` (183,120 tokens) and one `harness_cancellation`; re-entry logging itself is clean (5 clusters after the first, 5 `Re-entering` markers). The most likely shape is loss on a dispatch boundary — a task whose completion landed in the same turn the dispatch terminated — which is the failure mode lesson 2026-05-08-14-001 already describes.

## Proposed action

Routed as a RECURRENCE observation rather than a new lesson. The orchestrator holds the cross-plan context needed to decide whether this reinforces 2026-05-08-14-001 or names a distinct cause. Concretely worth checking: whether the two unpaired tasks completed adjacent to the `error` and `harness_cancellation` terminations, which the per-task `changed_files` capture proposed separately would make answerable offline.

## Evidence

- aspect: logging_gap_analysis — OUTCOME_COVERAGE expected_min 13, observed 11; error-severity finding
- aspect: log_analysis — phase5_logging_gaps.outcome_pairing paired 11, unpaired_completed [TASK-008, TASK-011], unpaired_outcome []
- aspect: log_analysis — dispatch_boundaries.5-execute: 1 error (183,120 tokens), 1 harness_cancellation, 3 budget_yield, 2 clean_exit_queue_empty, 1 voluntary_checkpoint
- RE_ENTRY_COVERAGE is clean (5 expected, 5 observed), so this is not a re-entry logging gap
