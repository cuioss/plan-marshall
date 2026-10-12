envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:12Z

# Candidate lesson: phase skills self-transition before the orchestrator's quality check runs

- Component: plan-marshall:plan-marshall
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-14-005 (created 2026-10-10), epic pm-mcp-core-m2-m4

- Component: plan-marshall:phase-2-refine, plan-marshall:phase-3-outline, plan-marshall:phase-4-plan (phase transition ownership) vs plan-marshall:plan-marshall orchestrator
- Signal: Q-Gate ordering (reported by the finalize dispatcher)
- Evidence: dispatcher observation. Partly visible in the work log: phase-3-outline logged "Q-Gate: pending
  (validation runs after phase return)" at 2026-10-09T21:19:58Z and q-gate-validation was dispatched afterwards
  (21:20:33Z); the self-transition itself is not logged as a separate line here.

## What happened (as reported)

refine, outline and plan each advance the plan's phase themselves before returning, while the orchestrator's
Q-Gate validation for that phase runs only after the return. When the Q-Gate then flags a finding (as 44f2ed did
in 3-outline), the status already shows the next phase, and the re-dispatch for the fix runs against an advanced
phase.

## Suggested direction

Leave the phase transition to the orchestrator after its Q-Gate passes (the phase-5-execute pattern in this run:
"transition left to the orchestrator as instructed"), or have the phase skill transition only when no
post-return Q-Gate is required.

Source: inbox `lock-manager-and-leases-009.md`, plan lock-manager-and-leases (PLAN-01, #20).
