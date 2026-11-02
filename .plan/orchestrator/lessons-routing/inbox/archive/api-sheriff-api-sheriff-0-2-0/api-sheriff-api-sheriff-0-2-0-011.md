envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T09:32:39Z

# Candidate lesson: phase-3-outline and phase-4-plan leaves advance the phase themselves

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 002. Suggested route: plan-marshall (phase-3-outline / phase-4-plan transition ownership).

Recurrence: the same class (outline/plan subagents moving the phase status themselves) was filed in API-Sheriff as lesson 2026-10-05-13-002.



**Signal:** orchestrator observation, partly evidenced in the work log.

## What happened

- The first phase-3-outline leaf returned with "Q-Gate: pending" (2026-10-15T16:09:40Z), yet the plan was already in `4-plan` when the orchestrator acted on the outline Q-Gate findings 272f23 and dc1bab. To run the fix pass, the orchestrator had to issue `set-phase` back: work-log row ed032a, `Phase: 4-plan -> 3-outline` at 16:21:08Z. The re-entry leaf then logged "transition left to orchestrator" (16:28:34Z), which is the intended behaviour.
- The orchestrator reports the same thing for phase-4-plan (4-plan -> 5-execute self-transition before the plan Q-Gate result was acted on). This lesson-capture pass could not find a separate set-phase row for that in the work log, so that half rests on the orchestrator's observation.

## Why it matters

Phase transitions belong to the main-context orchestrator. When a leaf advances the phase while a Q-Gate is still pending, the gate's fix loop has to rewind the phase first, and a fix pass on stale phase state is easy to miss.

## Suggested corrective action

Phase-3/phase-4 leaves should never call the phase transition when `qgate_validation_required=true`. They should return and leave the transition to the orchestrator after the Q-Gate settles. A post-return assertion that `current_phase` is unchanged would catch a regression.
