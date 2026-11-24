envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:39Z

component=plan-marshall:plan-marshall
category=bug
title=phase_handshake reported drift at 4-plan after the q-gate resolved its own findings
source_lesson=2026-11-23-14-008
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# phase_handshake reported drift at 4-plan after the q-gate resolved its own findings

# Candidate lesson: phase_handshake reported drift at 4-plan after the q-gate resolved its own findings

Source: script-failure cluster `plan-marshall:plan-marshall:phase_handshake` (exit 1, failure_kind=script_internal_failure) at 2026-11-23T07:48:04Z. Phase 4-plan, override false, drift_count 3:

- task_state_hash 032e62fad0ca11fd -> ad217a49e6848bd0
- qgate_open_count 2 -> 0
- pending_findings_blocking_count 4 -> 0

Component: plan-marshall:plan-marshall (phase_handshake), together with the q-gate-validation dispatch that follows phase-4-plan

## What happened

The 4-plan handshake was captured when phase-4-plan returned, with 2 open q-gate findings and 4 blocking findings. The orchestrator then dispatched q-gate-validation, which resolved them and changed tasks. The verify step at the 4-plan -> 5-execute boundary compared against the stale capture and reported drift. The run continued (worktree created, 5-execute dispatched), so the drift was the expected result of the q-gate step, not a real inconsistency.

## Candidate rule

When a phase's q-gate-validation runs after the phase has returned, capture the handshake again after the q-gate completes, or exclude q-gate-owned invariants from the pre-q-gate capture. Otherwise every plan with `qgate_validation_required=true` at 4-plan reports drift as a script failure, which adds noise to the lesson signal.
