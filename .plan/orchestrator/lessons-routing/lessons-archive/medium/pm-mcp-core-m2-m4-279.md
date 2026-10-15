envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:48Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-025.md
> NEW; related to -258 (domain detector keyed on one word). Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# change_type heuristic classified an audit-trail feature as "verification"

- Source: plan work log c9b372 (2026-10-14T07:42:52Z, phase 1-init): "(change-type-heuristic) Detected change_type=verification (confidence=1.0)", overridden 8 s later by 852e9f "Metadata: change_type=feature". Orchestrator-observed signal, corroborated by the log.
- Suggested component: `plan-marshall:phase-1-init` (change-type heuristic) / `plan-marshall:manage-status`.

## Observation

The request was "anchored audit trail with hash chain and verification" — new packages, formats, rotation, ADRs. The heuristic reported `verification` at confidence 1.0, apparently keyed on the word "verification" in the title. A confidence of 1.0 on a keyword hit is overconfident; the operator/orchestrator had to override it.

## Candidate rule

The change-type heuristic should not score a single keyword as certainty; a request that creates new production code should outrank a "verification" keyword, and keyword-only matches should cap below the auto-accept threshold.
