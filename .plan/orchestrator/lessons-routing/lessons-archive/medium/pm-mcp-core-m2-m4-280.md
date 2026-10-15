envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:49Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-026.md
> RECURRENCE of -026, -066, -089, -172, -223, -236, -255. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Phase bodies self-transitioned phases, forcing the orchestrator to reconcile boundaries

- Source: plan work log 5f8dd1 (08:19:46Z): "Post-outline main-checkout assertion passed (clean); 3-outline already transitioned by the phase body", followed by two manual "Phase: 4-plan -> 3-outline" resets (ed032a at 08:25:59Z and 08:41:47Z) to re-run the outline after Q-Gate. Orchestrator-observed signal (metrics boundary reconciliation), corroborated by the log.
- Suggested component: `plan-marshall:phase-3-outline` / `plan-marshall:plan-marshall` (phase transition ownership) / `plan-marshall:manage-metrics`.

## Observation

The outline phase body transitioned 3-outline -> 4-plan itself while Q-Gate validation was still pending (qgate_validation_required=true), so each Q-Gate loop had to move the plan back from 4-plan to 3-outline, and the per-phase metrics boundaries no longer matched the work done. The orchestrator reported the same for execute envelopes.

## Candidate rule

Exactly one owner transitions a phase. When a phase returns `qgate_validation_required=true`, the phase body must not transition; the orchestrator transitions after the Q-Gate passes, so metrics boundaries are recorded once and correctly.
