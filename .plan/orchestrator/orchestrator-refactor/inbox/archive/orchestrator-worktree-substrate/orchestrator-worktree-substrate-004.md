envelope_version=1
sender_type=plan
sender_id=orchestrator-worktree-substrate
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-28T19:16:54Z

component=plan-marshall:phase-3-outline
category=bug

# Reject an outline whose CERTAIN_EXCLUDE assessment names a declared affected file

## Context

In orchestrator-worktree-substrate, phase-3-outline assessed `manage-logging/SKILL.md` as CERTAIN_EXCLUDE. The same outline also declared that file `write-replace` in deliverable 5, and the file was then modified. Separately, the realized footprint carried 9 undeclared test modules, and one declared test (`test_orchestrator_scope.py`) was never modified. Its coverage moved to the undeclared `test_orchestrator_use_worktree.py`.

## Root cause

Outline validation never checks the per-file assessments against the deliverables' declared file lists, so the outline can contradict itself. After execute, nothing reconciles the declared lists with the realized footprint, so later drift is reported only at retrospective time.

## Proposed action

Add an outline-validation check that fails when a CERTAIN_EXCLUDE assessment names a path that a deliverable declares with modification intent. Consider a post-execute step that proposes updating the declared lists from the realized footprint, so the declaration a reviewer reads matches what shipped.

## Evidence

- aspect: outline_vs_shipped - exclude_violated 1 of 4 (manage-logging/SKILL.md)
- aspect: request_result_alignment - 9 scope-creep files, 1 declared-but-unrealized test
- aspect: manifest_decisions - declared_vs_realized_set fail (1 outline_only, 11 references_only)
- aspect: artifact_consistency - recall 98.1%, missing test_orchestrator_scope.py
