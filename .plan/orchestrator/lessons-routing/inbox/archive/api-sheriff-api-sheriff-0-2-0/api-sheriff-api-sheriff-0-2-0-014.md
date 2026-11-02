envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-17T09:32:40Z

# Candidate lesson: deep-lane outline skipped CERTAIN_INCLUDE assessment persistence

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 005. Suggested route: plan-marshall (phase-3-outline deep lane / assessment recording).

RECURRENCE of the known 'deep-lane outline leaves the assessment store empty' class (e.g. pm-mcp-core-m2-m4-212 / -097 in this inbox's archive; API-Sheriff lesson 2026-10-04-09-003; routed earlier from PLAN-V02-26). Sixth API-Sheriff occurrence.



**Signal:** Q-Gate finding 272f23 (3-outline, warning, resolved `taken_into_account`).

## What happened

The first outline declared about 76 affected paths across 5 deliverables but recorded no CERTAIN_INCLUDE assessments (`findings_store_state: missing`). That tripped validator 2.2. The scope itself was complete: the deep lane ran a full `architecture search --content` consumer sweep over 705 files, and an independent Q-Gate re-sweep agreed. Only the persistence step was missing. The re-entry pass recorded 79 assessments (72 mutation + 7 read-intent), matching `sync-affected-files declared_count 79`.

## Suggested corrective action

In the deep lane, recording one CERTAIN_INCLUDE assessment per declared path should be a mandatory step that completes before the outline is written, for example with a self-check that the assessment count equals the declared count. That way a correct sweep does not cost a Q-Gate round trip just to write down what it already found.
