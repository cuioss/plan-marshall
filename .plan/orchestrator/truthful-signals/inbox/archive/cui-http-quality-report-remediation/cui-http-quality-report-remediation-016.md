envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T15:50:47Z

component=plan-marshall:phase-5-execute
category=bug

# Candidate lesson: scope_creep_check cannot persist its finding and counts upstream commits as scope creep

- Suggested component: plan-marshall:phase-5-execute (scope_creep_check) and plan-marshall:manage-findings
- Suggested category: bug
- Signal source: script-failure cluster (3 occurrences)
- Evidence: work log 5b10d1 at 11:51:13Z, 12:04:03Z and 13:01:57Z, `script_failure notation=plan-marshall:phase-5-execute:scope_creep_check exit_code=1 failure_kind=script_internal_failure detail=Invalid finding type: scope_creep_warning. Must be one of (...)`. Follow-up lines 998090, 737b61 and 9f47e7 say the residual was "52 files ... upstream main commits since plan_creation_sha, not TASK-9 edits".

## What happened

1. scope_creep_check emits a finding of type `scope_creep_warning`. manage-findings does not accept that type, so the check exits 1 with finding_persist_failed every time it runs. This plan hit it on every loop-back re-entry.
2. The check diffs from `plan_creation_sha`, so commits that landed upstream between plan creation and the worktree base count as plan scope creep.

## Why it matters

The check never produces a usable result, so the operator has to override it on every run. That trains the operator to ignore the scope-creep gate.

## Suggested fix

- Either add `scope_creep_warning` to the manage-findings type enum, or map the check's output to an existing type. Add a contract test between the producer and the consumer's type set.
- Diff against the worktree base or merge-base, not `plan_creation_sha`.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-13 (cuioss/cui-http #262), inbox message `plan-13-asciidoc-specs-requirements-adrs-003.md`. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
