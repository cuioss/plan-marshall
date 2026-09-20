envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:53:09Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=log_analysis,logging_gap_analysis

# Task completion emitted no [ARTIFACT] line for 17 of 18 tasks

## Context

`analyze-logs` reports `artifact_emission.completed_tasks: 18`, `tasks_with_artifacts: 1`, and names the 17 silent tasks (TASK-001, TASK-003 … TASK-018). The plan landed 16 files across 9 deliverables, so the great majority of those 17 tasks were not empty-diff tasks whose silence would be legitimate.

The two halves of the check failed together in the same run:

- `ARTIFACT_EMISSION_PARTIAL` fired (1 of 18).
- `ARTIFACT_COVERAGE_UNMEASURABLE` also fired, because the footprint could not be resolved — so the rule that would have decided *which* of the 17 silent tasks had a non-empty diff could not run.

The result is a warning that cannot be sized. The retrospective can say emission was sparse; it cannot say how much of the sparseness is a defect.

## Root cause

`phase-5-execute` is documented to emit one `[ARTIFACT]` entry per file operation at task completion. The `[OUTCOME]` channel is healthy — `outcome_pairing` shows 18 paired, 0 unpaired in either direction — so tasks did complete and did announce completion. What is missing is the artifact emission that is supposed to accompany a completion carrying file changes. The emitting path was bypassed, not legitimately silent.

Note the interaction with the second finding: the `ARTIFACT_EMISSION` rule's non-empty-footprint floor is disabled exactly when the footprint is unresolvable, which is the same condition that makes the gap hard to size. Two checks that were meant to back each other up fail from one shared cause.

## Proposed action

- Restore `[ARTIFACT]` emission at task completion in `phase-5-execute`, and make it derivable from the task's own diff against `task_start_sha` so it cannot silently drop.
- Publish the per-task diff-emptiness alongside the emission count, so `ARTIFACT_EMISSION_PARTIAL` reports "N of M tasks with a non-empty diff emitted nothing" rather than a bare ratio over all completed tasks.
- Do not let the unresolvable-footprint condition disable the per-task branch: the per-task diff is computable from `task_start_sha` without the plan-wide footprint resolver.

## Evidence

- aspect: log_analysis — `artifact_emission: completed_tasks: 18, tasks_with_artifacts: 1, tasks_without_artifacts[17]`
- aspect: log_analysis — `ARTIFACT_EMISSION_PARTIAL: 1 of 18 completed task(s) emitted >= 1 [ARTIFACT] line (17 emitted none)`
- aspect: log_analysis — `ARTIFACT_COVERAGE_UNMEASURABLE: ... so ARTIFACT coverage could not be graded (artifact_entries=23)`
- aspect: log_analysis — `outcome_pairing: paired: 18, unpaired_completed[0], unpaired_outcome[0]` (the completion channel itself is intact)
