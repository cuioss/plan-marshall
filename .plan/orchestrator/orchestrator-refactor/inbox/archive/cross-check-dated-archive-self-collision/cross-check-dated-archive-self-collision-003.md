envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:18Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Persist the scope-creep finding under a type manage-findings accepts

## Context

`plan-marshall:phase-5-execute:scope_creep_check check` exited 1 on all three calls in this plan. The guard had measured an over-threshold result each time (6, then 16 residual files against a threshold of 5) and could not record it: the finding reached no store and travelled only in the leaf's return text and the logs.

## Root cause

The script persists with finding type `scope_creep_warning`, and `manage-findings` rejects it: "Invalid finding type: scope_creep_warning. Must be one of ('bug', 'improvement', 'anti-pattern', 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow')".

Still present at 8665ddacf: a content search finds the literal in `phase-5-execute/scripts/scope_creep_check.py` (4), `phase-5-execute/SKILL.md` (3), `test_scope_creep_check.py` (4) and `test_qgate_persist_contract.py` (1). The tests pass while the real call fails, so they do not drive the real type validation (how they avoid it was not read).

## Proposed action

Persist under an accepted type, or add `scope_creep_warning` to the allowed set in `manage-findings` - one or the other, in the script, the SKILL.md and both tests together. Add a test that runs the persist call against the real findings validator so the two vocabularies cannot drift apart again.

## Evidence

- script-failure-analysis: 3 failures, 1 unique, `script_internal_error`, first at 2026-10-01T07:35:37Z
- work.log ERROR lines 2026-10-01T07:35:37Z, 10:01:31Z, 10:10:44Z
- decision.log 2026-10-01T07:36:34Z, 10:01:38Z, 10:10:57Z (each notes the finding is in no store)
