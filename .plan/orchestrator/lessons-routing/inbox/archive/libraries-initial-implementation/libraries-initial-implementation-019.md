envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:12Z

component=plan-marshall:phase-3-outline
category=bug
title=phase_handshake reports drift after the orchestrator resolves the phase's own Q-Gate findings
source_lesson=2026-11-18-18-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# phase_handshake reports drift after the orchestrator resolves the phase's own Q-Gate findings

# Candidate lesson: phase_handshake reports drift after the orchestrator resolves the phase's own Q-Gate findings

- Source signal: plan git-worktrees-import (inbox plan-03-git-worktrees-import-003), script-failure cluster, notation `plan-marshall:plan-marshall:phase_handshake`, phase 3-outline to 4-plan transition.

## What happened

The 3-outline invariants were captured while two Q-Gate findings were pending. The orchestrator then resolved both as `taken_into_account` and called `phase_handshake`, which returned `status: drift` (exit 1) with the diffs `qgate_open_count 2 -> 0` and `pending_findings_blocking_count 2 -> 0`. The orchestrator re-captured the 3-outline invariants and went on. The drift was its own legitimate resolution, not an out-of-band change.

## Candidate rule

Resolving the phase's own Q-Gate findings between capture and verify is the expected path, not drift. Either document a re-capture of the invariants after Q-Gate resolution as a step of the phase, or let `phase_handshake` treat a decrease in the open and blocking Q-Gate counts that resolved findings explain as non-drift.


## Recurrence in a later plan (plan-23-forms-hardening, inbox plan-23-forms-hardening-003)

- Source signal: script failure, notation `plan-marshall:plan-marshall:phase_handshake` (work log 07:52:51, exit_code=1, `script_internal_failure`). The 4-plan handshake captured `qgate_open_count=2` and `pending_findings_blocking_count=2` while two `skills_by_profile` Q-Gate findings were pending; the operator accepted both at 07:52:11-12; the verify at 07:52:51 reported `status: drift`, drift_count 2, captured "2", observed "0". The run continued into 5-execute.
- A drift in the helpful direction (a blocking count that went DOWN because the operator resolved the findings) is reported as a script failure exactly like a harmful one, so every plan where the operator accepts a 4-plan Q-Gate finding produces a false failure. Two options: the orchestrator re-captures the handshake after an operator resolves boundary findings and before it verifies, or `phase_handshake` treats a decrease of a blocking-count invariant, explained by recorded resolutions, as non-drift.
