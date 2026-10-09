envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:51Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Fix scope_creep_check: unaccepted finding type and stale baseline SHA

## Context

On plan lb-23-verify-builds `plan-marshall:phase-5-execute:scope_creep_check check` exited 1 on every invocation (6 failures in the script-execution log) with `finding_persist_failed`. Every execute dispatch logged it once and carried on, so the guard gave no signal for the whole plan.

## Root cause

Two independent defects:

1. The script files its result as finding type `scope_creep_warning`, which `manage-findings` rejects: "Invalid finding type: scope_creep_warning. Must be one of ('bug', 'improvement', 'anti-pattern', 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow')".
2. It measures against `plan_creation_sha`, so upstream commits that landed between plan creation and the branch base count as scope creep: 76 residual files on the first task (exactly the upstream diff between 524cebbb7 and 964d0bb4d, none of them task edits), 77 later, 108 in the last round, against a threshold of 5.

## Proposed action

- File the result under an accepted finding type (or add the type to the declared vocabulary in the same change as its producer).
- Measure against the branch base / merge base, not the plan creation SHA, and re-anchor after a baseline absorb.
- Add a test that runs the guard end to end against a real findings store, so a rejected type fails the test rather than every plan.

## Evidence

- aspect: script_failure_analysis - `plan-marshall:phase-5-execute:scope_creep_check`, subcommand `check`, exit 1, `script_internal_error`, 6 occurrences, first at 2026-10-08T21:05:06Z.
- work log 2026-10-09T07:27:11Z: the rejection message quoted above.
- aspect: chat_history_analysis - first execute hand-back: "It measured 76 files over a threshold of 5. Those 76 are exactly the upstream commits between plan_creation_sha 524cebbb7 and the branch base 964d0bb4d".
