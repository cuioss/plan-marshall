envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:04:12Z

# Make scope_creep_check persist a finding type manage-findings accepts

component: plan-marshall:phase-5-execute
category: bug

## Context

During phase 5 of ledger-decomposition-and-row-vocabulary, `plan-marshall:phase-5-execute:scope_creep_check check` failed 7 times with exit 1 (`finding_persist_failed`). Each time it computed a real signal (residual 12 files over threshold 5) and then tried to persist it as finding type `scope_creep_warning`, which manage-findings rejects. The signal survived only as an ERROR line in work.log, never as a finding.

## Root cause

The check writes a finding type (`scope_creep_warning`) that is missing from the manage-findings type enum ('bug', 'improvement', 'anti-pattern', 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow'). Nothing checks the producer's type against the consumer's accepted set.

## Proposed action

Either map the check onto an accepted type (e.g. `triage` or `insight` with a scope-creep discriminator), or add `scope_creep_warning` to the manage-findings enum. Add a test that pins every finding type scope_creep_check can emit to the accepted set, derived from the enum rather than a copy of it.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:phase-5-execute:scope_creep_check` script_internal_error, occurrence_count 7
- aspect: logging_gap_analysis — work.log ERROR `finding type scope_creep_warning rejected by manage-findings; residual 12 files, threshold 5`
