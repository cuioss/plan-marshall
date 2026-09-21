envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:33:23Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-09-05
bundle=plan-marshall

# Record changed_files on completed task records so ARTIFACT_EMISSION can measure

## Context

The `ARTIFACT_EMISSION` rule in logging-gap-analysis is specified as a population check:
`N of M change-qualified completed tasks emitted at least one [ARTIFACT] line`, where `M`
counts completed tasks **whose own task diff is non-empty**. Its contract is explicit that
the qualification needs each task's own realized change set, and that this is available
offline only when a task record carries a `changed_files` list.

On this plan the extractor reported:

```text
change_attribution: unavailable
change_attribution_reason: "no completed task record carries a changed_files list, so no
  task diff could be attributed; the eligible-task population is omitted rather than
  reported as zero, and no emission finding is made"
```

Per the contract that is the correct behaviour — `eligible_tasks`, `eligible_tasks_with_artifacts`
and `eligible_tasks_without_artifacts` are ABSENT rather than zero, and no finding is
emitted. The rule degraded honestly. It also did not run.

## Root cause

Nothing writes `changed_files` onto a completed task record. The contract notes that the
per-task SHA range Step 8 diffs "is not persisted in a stable place", so the field the rule
depends on is never populated by the normal execute path.

The consequence is structural rather than per-plan: with no producer for the field, the
`unavailable` branch is not an edge case this plan happened to hit — it is the branch every
plan takes. A detector whose measuring branch is unreachable can fire on no plan at all,
while its `unavailable` path keeps reporting cleanly and looking like coverage.

This is the second instance in this one retrospective of a check that cannot look being
easy to mistake for a check that looked (see the sibling candidate on
`check-outline-vs-shipped`), and it is worth treating as an archetype rather than two
unrelated defects.

## Proposed action

Persist each task's realized change set at task completion — the point where the per-task
SHA range is still known — onto the task record as `changed_files`, including the empty
list when the task changed nothing. The empty list is load-bearing: the contract treats a
present-but-empty list as a MEASUREMENT ("this task changed nothing") and only an ABSENT
key as unavailable, and it is what lets a compliant no-op task stay out of `M` instead of
depressing `N/M`.

Note the contract's stricter requirement while implementing: `measured` requires the list
on EVERY completed task, not at least one. A partial rollout leaves the state MIXED, which
the contract also routes to `unavailable` — so a half-populated field buys no coverage.

## Evidence

- aspect: log_analysis — `artifact_emission.change_attribution: unavailable`, `completed_tasks: 4`, `tasks_with_artifacts: 4`
- aspect: logging_gap_analysis — `ARTIFACT_EMISSION expected_min unavailable / observed unavailable`
- `references/logging-gap-analysis.md` — "When per-task change attribution is unavailable, emit NO finding"
