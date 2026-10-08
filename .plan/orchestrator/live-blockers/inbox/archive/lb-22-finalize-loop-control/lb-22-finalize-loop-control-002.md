envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:56:55Z

component=plan-marshall:phase-5-execute
category=bug
source_plan=lb-22-finalize-loop-control
confidence=high

# Make scope_creep_check persist its finding and measure from the branch point

## Context

`plan-marshall:phase-5-execute:scope_creep_check check` failed with exit 1 and `error: finding_persist_failed` on every call where it had something to report. The retrospective's script-failure aspect counts 9 such failures, the first at 2026-10-08T12:57:45Z. While the measured residual stayed at or below the threshold of 5 the guard returned cleanly and filed nothing; from the first call where the residual reached 6 it failed every time, so the guard never produced a finding in this plan.

It also measured the wrong population. The first residual set (3 files) was `.plan/orchestrator/live-blockers/{epic,queue-view,resume_anchor}.md`, which no branch commit touched. After the finalize rebase onto `origin/main` the same call reported 5625 residual files.

## Root cause

Two independent defects:

1. The script files its finding under type `scope_creep_warning`, and the findings store rejects that type. Work-log entry at 2026-10-08T19:21:31Z: `Invalid finding type: scope_creep_warning. Must be one of ('bug', 'improvement', 'anti-pattern', 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow')`.
2. The diff base is `plan_creation_sha`, not the branch point. Commits that landed on main between plan creation and branch creation (here `fdbb6b6a2`), and every upstream commit a rebase brings in, are counted as the plan's own scope creep.

## Proposed action

- File the finding under a type the store accepts, or register `scope_creep_warning` in the store's type set, and add a test that runs the persist path against the real store rather than a stub.
- Measure from the merge base of the branch and its base branch (the same base the realized-footprint capture uses), so upstream history can never count.

## Evidence

- aspect: script_failure_analysis - `bug,script_internal_error,plan-marshall:phase-5-execute:scope_creep_check,check,1` with `occurrence_count: 9`.
- aspect: chat_history_analysis - execute leaves reported the failure five times, with residual counts 6, 9, 11 and finally 5625 after the rebase; one leaf traced the three `.plan/orchestrator/` files to main commit `fdbb6b6a2`, between `plan_creation_sha` `a8d0ebb2c` and the branch point.
- source: `scope_creep_warning` and `plan_creation_sha` each appear 4 times in `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` at main `6b00815e0`.
