envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-10-15T12:24:57Z

# Recurrence: verification-feedback has no producer value for the ci-verify caller (lessons-routing-019 / PLAN-LB-24)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 023 (orchestrator-observed; plan work log 2026-10-15T07:10:22Z, where ci-verify dispatched verification-feedback as ci-verify-triage and that led to TASK-011).

## Observation

This recurs as already tracked under lessons-routing-019 ("Red-CI triage unreachable: ci-verify producers outside the accept-set"), PLAN-LB-24. The verification-feedback producer accept-set is build-runner, sonar, pr-comment, plugin-doctor, pr-state, finalize-feedback. No value names ci-verify, so the ci-verify dispatch borrows a producer whose Step 1 branch was written for another caller.

## Disposition request

Fold this as a recurrence into lessons-routing-019 / PLAN-LB-24. Do not open a new item.
