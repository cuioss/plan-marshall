envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:55Z

# Candidate lesson: "mirror this exemplar" task text imports the exemplar's rationale prose (phase-4-plan)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 019 (Q-Gate 01aaa9, framing_rule).

## Observation

TASK-5 and TASK-7 told the executor to model a new log record and its doc entry on an existing one. The exemplar carries a rationale sentence the plan's wording rules did not allow. The tasks stated the wording rule only in general terms, so copying by analogy would likely have carried the sentence over.

## Candidate rule

When a task says "do it like X", it also says which parts of X to copy (layout, structure) and which not to (rationale, justifications). A general wording rule does not cover text the task tells the executor to mirror.
