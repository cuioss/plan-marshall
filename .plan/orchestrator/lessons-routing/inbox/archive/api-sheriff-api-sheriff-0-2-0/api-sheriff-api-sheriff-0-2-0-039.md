envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-21T12:52:15Z

# Candidate lesson: q_gate_validation=once leaves outline warning findings pending into execute (plan-marshall:plan-marshall Q-Gate loop-back)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-42-validator-auth-oidc-rules (PR cuioss/API-Sheriff#502), source message 004.

RECURRENCE: same class as api-sheriff-api-sheriff-0-2-0-021 (PLAN-V02-40). Here a real under-coverage warning (a second doc naming the moved member's owner) was fixed only because someone read the pending findings by hand.

**Routing:** process candidate (project configuration and plan-authoring practice).
**Suggested component:** plan-marshall:phase-3-outline (process)
**Category:** improvement

## What happened

Under `q_gate_validation=once`, the PLAN-V02-42 outline Q-Gate ran a single time and left two
warning findings pending into phase 4:

- 2130b9: profile overlap. Deliverable 1 carried a module_testing profile next to deliverable 2's
  test files. It was accepted as intended, because TASK-2 is the behaviour-neutral proof run.
- 5398c9: under-coverage. doc/development/bff-session.adoc also names ConfigValidator as the
  caller of OidcConfig.usesClientSecret(), the same ownership claim deliverable 3 corrected in
  bff-cookie.adoc. It was fixed by adding a step to TASK-4 before execute.

The fix was cheap here, but only because someone read the pending findings before execute.
Nothing forces a decision on outline warnings when the gate runs once.

## Corrective action

When q_gate_validation=once leaves warning findings pending, resolve each one (accept with a
reason, or fold it into a task) at the phase-4 boundary, before execute starts. For move or
ownership refactors, the outline should list every doc that states the moved member's owner or
caller, found with a content sweep for the old class name. It should not stop at the docs named
in the request.
