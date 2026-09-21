envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:43:06Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-09-15
bundle=plan-marshall

# Emit an [OUTCOME] line for every completed task, not 40 of 44

## Context

Plan `architecture-store-query-truthfulness` completed 44 tasks, but `work.log` carries only 40 `[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN` lines. TASK-024, TASK-025, TASK-026 and TASK-041 reached `status: done` leaving no outcome line behind. The gap is the same shape lesson `2026-05-08-14-001` describes: completions lost on agent-initiated re-dispatch.

## Root cause

The `[OUTCOME]` emission sits on the task-completion path inside the execute envelope, so a task whose completion is recorded after the envelope yields (voluntary checkpoint, budget yield, baseline drift) can have its status written without the paired log line. This plan had 18 execute dispatches across 3 phase re-entries, which is exactly the condition that exposes it.

## Solution

Move the `[OUTCOME]` emission so it is driven by the status write rather than by the envelope's own completion path — or add a reconciliation at execute-phase exit that emits a line for any `status: done` task with no matching outcome line, naming the reconciliation as its source.

## Impact

Every consumer that counts completions from `work.log` under-reports. In this run the retrospective's own OUTCOME_COVERAGE check fired at `error` severity, and the log-analysis aspect reported 4 tasks in both `unpaired_completed` and `tasks_with_diff_no_outcome`.

## Evidence

- aspect: log_analysis — `outcome_pairing: paired 40, unpaired_completed [TASK-024, TASK-025, TASK-026, TASK-041]`
- aspect: logging_gap_analysis — `OUTCOME_COVERAGE expected_min 44, observed 40` (error)
- 5-execute dispatch termination causes: 8 voluntary_checkpoint, 5 budget_yield, 3 baseline_drift, 2 error over 18 rows
