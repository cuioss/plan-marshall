envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:44Z

component=plan-marshall:plan-marshall
category=bug
title=a planning phase that hands its Q-Gate to the orchestrator advances status.json itself, forcing a reconciliation stamp and a manual backward transition
source_lesson=2026-11-24-07-009
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# a planning phase that hands its Q-Gate to the orchestrator advances status.json itself, forcing a reconciliation stamp and a manual backward transition

Source: orchestrator-observed fact, confirmed by the plan's work log.

Evidence:
- 2026-11-23T16:38:18Z: phase-3-outline returned "Q-Gate: pending". The orchestrator then dispatched q-gate-validation (16:43:58Z to 16:49:42Z).
- 16:50:18Z: "Resume reconciliation: stamped missing metrics boundary 3-outline -> 4-plan (phase-3-outline self-transitioned before the orchestrator boundary call)".
- 16:51:01Z: the orchestrator had to move the phase back, "Phase: 4-plan -> 3-outline", to re-dispatch the outline with the five findings.
- Same shape at 4-plan: phase-4-plan returned with qgate_validation_required=true (17:03:14Z), then after the Q-Gate pass "Phase: 5-execute -> 4-plan" (17:06:38Z) was needed to re-run planning for finding afd2ca.

Observation: when the phase returns "Q-Gate pending" or qgate_validation_required=true, the phase itself already advanced status.json. That costs a reconciliation stamp and a manual backward transition for every Q-Gate that finds something.

Candidate rule (probably framework-side): a phase that hands its Q-Gate to the orchestrator does not change the phase itself; the orchestrator changes it after the Q-Gate passes.

Context: plan plan-20-leftover-fixes-2.


Source: inbox plan-20-leftover-fixes-2-014. Related: 2026-11-23-14-008 and 2026-11-18-18-002 (phase_handshake drift after the Q-Gate resolves its own findings).
