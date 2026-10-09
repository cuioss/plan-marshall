envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:21Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-10-09

# Let scope_creep_check persist its finding and measure from the branch base

## Context

During plan `plan-lb-29-harness-sync` the execute-phase scope-creep guard (`plan-marshall:phase-5-execute:scope_creep_check check`) exited 1 six times. Each time it had measured a residual above its threshold of 5 and then failed with `error: finding_persist_failed`, because the findings store answered `Invalid finding type: scope_creep_warning`. No finding was ever recorded, so the one case the guard exists for (9 undeclared files against a threshold of 5) left nothing in the findings store. On its first run the guard also reported `residual_count: 5616`, dominated by `.plan/archived-orchestrators/**` and `.github/workflows/**` paths the plan never touched.

## Root cause

Two separate defects. The guard emits a finding type the findings store does not accept. And its diff base was `plan_creation_sha` (`fdbb6b6a2`), which was older than the branch base (`3fe828c84`), so upstream commits were counted as plan work. The second cause was inferred by the executing step from the commit list and file names; it was not confirmed with a merge-base check.

## Proposed action

- Register `scope_creep_warning` as an accepted finding type in the findings store, or change the guard to file under a type the store already accepts, and add a test that the guard's own finding round-trips through the store.
- Measure the residual from the merge base of the branch and its base ref rather than from the recorded creation sha, so main advancing between plan creation and worktree creation does not count as scope creep.
- When persisting fails, keep the measured residual in the result so the caller can still act on it.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:phase-5-execute:scope_creep_check check`, exit 1, `script_internal_error`, 6 occurrences, first at 2026-10-08T15:02:39Z.
- aspect: chat_history_analysis — executing steps reported `finding_persist_failed`, `Invalid finding type: scope_creep_warning`, `residual_count: 5616` against `threshold: 5` on the first run, and 9 residual files against 5 from deliverable 8 onward with no finding stored.
- aspect: request_result_alignment — 26 files outside the declared surface were modified; none of that drift is visible in the findings store.
