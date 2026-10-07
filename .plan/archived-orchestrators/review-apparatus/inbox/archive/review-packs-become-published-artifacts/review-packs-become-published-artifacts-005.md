envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:33:21Z

# Emit an [OUTCOME] line for every completed task, including on re-dispatch

component: plan-marshall:phase-5-execute
category: bug
confidence: high

## Context

The plan completed 11 tasks. `work.log` carries only 10 `[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN` lines. TASK-010 ("Separate two direct submits that differ only in explicit --timeout") reached `status: done` with `4/4` steps and emitted no outcome line.

A second, independent check in the same fact extractor — `outcome_for_diffed_tasks` — names the same task under `tasks_with_diff_no_outcome`. So TASK-010 produced a non-empty diff and is not a compliant no-op whose silence would be expected.

## Root cause

This plan re-entered 5-execute four times (`close_count: 4`) and the recorded 5-execute dispatch terminated with `termination_cause: voluntary_checkpoint`. That is the exact condition lesson `2026-05-08-14-001` describes: the outcome line is lost when the agent re-dispatches itself, because the emitting step sits after the checkpoint boundary in the task loop.

The gap is self-concealing. `outcome_pairing` reports `paired: 10` and `unpaired_outcome: []`, which reads as healthy unless the reader compares against the 11 completed tasks rather than against the 10 paired lines.

## Proposed action

Emit the `[OUTCOME]` line before the voluntary-checkpoint yield can be taken, not after the task loop's continuation point, so a re-dispatch cannot swallow it.

Add an end-of-phase reconciliation that compares the `[OUTCOME]` line count against the count of tasks in `status: done` and fails loudly on a shortfall, rather than leaving the discrepancy to be found retrospectively.

## Evidence

- aspect: logging_gap_analysis — `OUTCOME_COVERAGE` expected 11, observed 10
- aspect: log_analysis — `phase5_logging_gaps.outcome_pairing.unpaired_completed: [TASK-010]` and `outcome_for_diffed_tasks.tasks_with_diff_no_outcome: [TASK-010]`, two independent checks naming the same task
- `metrics.toon` — 5-execute `close_count: 4`, `re_entered_phases: 5-execute`
- dispatch boundary — 5-execute row `termination_cause: voluntary_checkpoint`
- Recurrence of lesson 2026-05-08-14-001
