envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:51Z

# Candidate lesson: assessments outlive a refuted design and contradict the re-outlined deliverables (phase-3-outline)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source messages: 003, 006 (Q-Gate 5b2431, da009b).

## Observation

After an early fix hypothesis was refuted, the re-outline moved DispatchStageTest.java onto D3's mutate list, but its assessment stayed CERTAIN_EXCLUDE from the old design. In a second round, two CERTAIN_INCLUDE assessments (one written for the refuted design, one conditional whose condition did not hold) matched no deliverable.

## Candidate rule

When a re-outline drops a design, re-check every assessment written for it in the same revision, and supersede each one whose verdict no longer matches the deliverable lists. A conditional assessment ("joins the mutate list only if X") is resolved as soon as X is decided.
