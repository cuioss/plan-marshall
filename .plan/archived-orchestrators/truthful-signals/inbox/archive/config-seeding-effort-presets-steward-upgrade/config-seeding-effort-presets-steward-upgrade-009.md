envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:42:37Z

component=plan-marshall:phase-5-execute
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# Task-completion ARTIFACT emission fired on 4 of 26 tasks against a 62-file footprint

## Context

`phase-5-execute` is contracted to emit one `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` line per file operation at task completion. Across this run:

- 26 tasks completed;
- **4** of them emitted any `[ARTIFACT]` line at all (tasks 4, 7, 11, 12);
- **22** emitted none;
- total `[ARTIFACT]` entries: **20** — fewer than the 62 files the plan actually changed.

The 22 silent tasks are not empty-diff tasks. At least 13 are implementation-profile tasks identifiable from their own titles (each is paired with a sibling "Test X" task): TASK-002, 006, 008, 010, 014, 016, 018, 020, 022, 023, 024, 025, 026. Every one completed. TASK-008 ("marshal.json write paths and the schema they write into") alone accounts for `_config_core.py`, `_providers_core.py` and `upgrade.py` in the landing diff, and announced nothing.

The consequence is not cosmetic. The `ARTIFACT_EMISSION` rule in `logging-gap-analysis` is one of the guards on whether the plan's declared work matches its actual work, and it can only measure what was emitted. With 4/26 coverage the guard grades a sample, not a population — the recurring "volume-read-as-coverage" archetype, here applied to the guard rather than by it.

Two neighbouring emissions in the same phase were **complete**, which is what makes this specifically an ARTIFACT problem rather than general log sparseness:

- `[OUTCOME]` coverage: 26 tasks done, 26 `Completed TASK-NNN` lines, 0 unpaired in either direction — across 10 dispatch clusters and one full loop-back.
- Re-entry coverage: 10 dispatch clusters, 1 `Starting` marker, 9 `Re-entering` markers — exact.

So the phase's other two per-task emissions held perfectly under the same conditions that dropped 85% of ARTIFACT lines.

## Root cause

Not established from the logs. The four emitting tasks (4, 7, 11, 12) are spread across three different dispatch clusters, so it is not a single lost envelope. The emitting path appears to be reached opportunistically rather than as a mandatory step of task completion, in the way `[OUTCOME]` clearly is — `[OUTCOME]` is emitted adjacent to `manage-tasks Completed` on every single task, while `[ARTIFACT]` is not tied to any such anchor.

## Proposed action

1. Bind `[ARTIFACT]` emission to the same completion anchor `[OUTCOME]` uses, so the two are emitted together or neither is — an `[OUTCOME]` line with a non-empty task diff and no accompanying `[ARTIFACT]` should be structurally impossible.
2. Derive the per-task file set from the task's own diff against its `task_start_sha` rather than relying on the executing agent to recall what it touched.
3. Have the `ARTIFACT_EMISSION` check publish its coverage denominator (tasks with a non-empty diff) alongside its count, so a 4/26 result cannot read as "4 tasks changed files".

## Evidence

- aspect: `log_analysis` → `artifact_emission.completed_tasks: 26`, `tasks_with_artifacts: 4`, `tasks_without_artifacts[22]`; finding `ARTIFACT_EMISSION_PARTIAL`.
- aspect: `logging_gap_analysis` → `expected_vs_actual` rows `ARTIFACT 26/20 fail` and `ARTIFACT_EMISSION 15/2 fail`; `outcome_coverage` and `re_entry_coverage` both pass exactly.
- aspect: `request_result_alignment` → `realized_files: 62`.
- `logs/work.log` — the only `[ARTIFACT] (plan-marshall:phase-5-execute:N)` lines are at 18:34 (task 4, 3 files), 19:40 (task 7, 3 files), 20:52 (task 11, 1 file), 21:02 (task 12, 6 files).
