envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:53Z

# Candidate lesson: a deliverable's risk-mitigation gate was not carried into the task text (phase-4-plan)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 017 (Q-Gate e0abfe).

## Observation

D2's risks_and_mitigations committed to checking, after the first diagnostic run, that the thread dump was actually written. TASK-2's description left that out. An executor following only the task could have spent all 100 runs without a usable dump. The gate ended up only in the orchestrator's dispatch prompt.

## Candidate rule

Every check stated in a deliverable's risks_and_mitigations appears in the description of the task that runs the risky step. For expensive diagnostic rounds, "verify the first run produced the evidence" comes before the rest of the round is released.
