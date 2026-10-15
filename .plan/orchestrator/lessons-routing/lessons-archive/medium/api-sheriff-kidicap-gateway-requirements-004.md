envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:52Z

# Candidate lesson: a documentation deliverable named its insertion point by paraphrase, and no such section existed (phase-3-outline)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 008 (Q-Gate a37449).

## Observation

D5 described a doc edit by what the target section was expected to contain. No such section existed. The nearest match conflicted with the plan's wording rules, so the edit was dropped and the file moved to the read set.

## Candidate rule

A documentation deliverable names its insertion point by an existing heading or anchor, verified in the file. If nothing fits, the outline says so and decides whether the edit belongs in that file at all.
