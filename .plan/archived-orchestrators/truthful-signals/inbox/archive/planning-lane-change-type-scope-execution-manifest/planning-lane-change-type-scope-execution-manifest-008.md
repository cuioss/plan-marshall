envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T16:02:16Z

# No completed task record persists changed_files, so ARTIFACT_EMISSION can never run

component: plan-marshall:manage-tasks
category: improvement
confidence: medium
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

The `ARTIFACT_EMISSION` invariant in `references/logging-gap-analysis.md` is specified in considerable detail: a population rule `N of M change-qualified completed tasks emitted >= 1 [ARTIFACT] line`, with `M` restricted to completed tasks whose **own** diff is non-empty, two findings partitioning the incomplete range (`ARTIFACT_EMISSION_PARTIAL` for `0 < N < M`, `ARTIFACT_EMISSION_ABSENT` for `N == 0 ∧ M >= 1`), and an explicit prohibition on substituting the un-qualified completed-task count for `M`.

On this plan the extractor reported:

```
artifact_emission:
  completed_tasks: 25
  tasks_with_artifacts: 8
  change_attribution: unavailable
  change_attribution_reason: "no completed task record carries a changed_files list, so no task
    diff could be attributed; the eligible-task population is omitted rather than reported as
    zero, and no emission finding is made"
```

`eligible_tasks`, `eligible_tasks_with_artifacts` and `eligible_tasks_without_artifacts` are **absent** from the payload, not zero — exactly as the contract requires.

## Root cause

The qualification needs each task's own realized change set. The reference states plainly that "the per-task SHA range Step 8 diffs is not persisted in a stable place", and the offline inputs carry it only when a task record holds a `changed_files` list. No task record on this plan carries one.

So the behaviour is correct and the contract is honoured — this is the system working, and it is worth recording as such. But the practical consequence is that the rule has, as far as this plan's evidence goes, never been evaluated on a real plan. A carefully-specified invariant that always reports `unavailable` is indistinguishable in effect from an invariant that does not exist, and the 8-of-25 `tasks_with_artifacts` figure sitting beside it is precisely the substitution the contract forbids and a hurried reader will make.

This plan itself shipped `task_start_sha` (deliverable 11, `capture_task_start_sha` in `_task_artifacts.py`), which is the per-task diff *baseline*. The other half — the realized set diffed against it at close — is computed in `_cmd_step.cmd_finalize_step` and then discarded to a count (`artifact_lines = len(...)`), which is the same field three separate Q-Gate findings on this plan (`aa9eaf`, `92afd1`, `36c7b8`) established cannot discriminate fired-from-not-fired.

## Proposed action

Persist the list, not just its length. `cmd_finalize_step` already has the diff in hand when it computes `artifact_lines`; writing it to the task record as `changed_files` costs one field and turns three things on at once:

- `ARTIFACT_EMISSION` becomes evaluable, with a real `M`.
- `artifact_lines: 0` gains the discriminator those three findings said it lacks — an empty `changed_files` is the measured zero, an absent key is the channel that never ran.
- `analyze-logs`' `change_attribution` can report `measured` instead of `unavailable`.

Note the contract's own strictness here: `measured` requires the list on **every** completed task, not on at least one, and a mixed corpus must report `unavailable` with a reason naming which state. A partial rollout does not partially enable the rule.

## Evidence

- aspect: log_analysis — `change_attribution: unavailable` with its reason; the three eligible-task keys absent rather than zero
- aspect: logging_gap_analysis — `ARTIFACT_EMISSION` reported as un-run, not clean; `8 of 25 tasks_with_artifacts` explicitly marked as provenance only and not the rule's population
- Q-Gate findings `aa9eaf`, `92afd1`, `36c7b8` (this plan) — all three established that `artifact_lines` as an int cannot separate a measured zero from a channel that never fired
