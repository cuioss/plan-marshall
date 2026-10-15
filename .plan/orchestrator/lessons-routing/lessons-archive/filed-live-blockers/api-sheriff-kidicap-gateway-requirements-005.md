envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:53Z

# Candidate lesson: staged (diagnose-then-fix) plans have no declared task deferral, so coverage and declared_set_closure fire on every deferred deliverable (phase-4-plan)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source messages: 009-016 (Q-Gate 4ff4fa, 26f8a3, 24e2b6 coverage, and 5356f5, 2e3e00, 47924f, 87e7c8, 950b8f declared_set_closure). Eight findings, all accepted by hand.

## Observation

The operator chose a staged plan: D2 diagnoses the cause, and tasks for D3-D5 are created by a second re-outline once D2 reports. The mechanical coverage check (every deliverable has a task) fired for D3, D4 and D5. declared_set_closure fired once for each provisional write path D3/D5 declared, so later gates would know the likely footprint. Every one was accepted as a deliberate gate.

## Candidate rule

Add a first-class declared deferral ("tasks deferred until deliverable N reports") that the coverage check honours, and that lets declared_set_closure skip or soften the provisional paths of a deferred deliverable. Until then, document that staged plans accept these findings with the deferral reason, so they stop reading as forgotten sweeps.
