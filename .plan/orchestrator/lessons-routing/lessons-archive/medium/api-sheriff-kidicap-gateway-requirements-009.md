envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:55Z

# Candidate lesson: an operator re-scope during finalize left a stale "unchanged" claim in the outline (phase-6-finalize loop-back)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 025.

## Observation

An operator decision during finalize added a stream cap to EdgeHardeningOptions (loop-back TASK-9). The outline still said that part of the configuration stayed "unchanged". Nothing re-read the outline's invariant sentences against the decision.

## Candidate rule

When an operator decision changes what a deliverable touches, update the outline in place in the same step. Search the deliverable prose and success criteria for "unchanged" or "not touched" claims about the newly touched files or options, and fix them before the loop-back task is created.
