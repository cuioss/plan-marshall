envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:50Z

# Candidate lesson: a success criterion names files its deliverable's Affected files omit (phase-3-outline)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source messages: 001, 004 (Q-Gate fb188c, 9c6874, scope_criterion_validator under_coverage).

## Observation

D1's criterion ("these files are unchanged on the plan branch", plus a revert arm) pointed at four files, but Affected files listed two. One of them also sat in a different directory than the prose implied. The same class then fired again on D3 ("Http2EarlyResponseResetIT.java is unchanged"), because the D1 fix was not applied across the other deliverables.

## Candidate rule

When a success criterion makes a claim about a file (unchanged, reverted, read), list that file as a (read) affected file of the same deliverable, at its verified on-disk path. Derive the list from the criterion text. When a Q-Gate finding is resolved for one deliverable, sweep every other deliverable for the same class before re-running the gate.
