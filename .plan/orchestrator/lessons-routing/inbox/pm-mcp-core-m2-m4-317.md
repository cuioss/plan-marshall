envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:31Z

component=plan-marshall:plan-marshall
category=bug
source=script-failure cluster, work log 1d51a4 (2026-10-17T15:26:59Z, phase_handshake exit 1)

# Phase handshake reports drift when the Q-Gate was legitimately resolved after capture

## Observation

At the 3-outline to 4-plan transition, `plan-marshall:plan-marshall:phase_handshake` returned `status: drift` (exit 1, script_internal_failure) with qgate_open_count captured 1, observed 0, and pending_findings_blocking_count captured 1, observed 0. The q-gate-validation dispatch had resolved the one open finding after the capture. The orchestrator proceeded to phase-4 anyway.

## Rule

A drift that moves toward fewer open findings, caused by a sanctioned resolve between capture and verify, is expected and should not surface as a script failure. Either re-capture after q-gate-validation, or classify a monotone decrease of open counts as benign so the failure marker stays meaningful.
