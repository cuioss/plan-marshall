envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:09Z

# Candidate lesson: phase leaves self-transitioned 3-outline and 4-plan before the orchestrator's Q-Gate ran

Source: run event in plan verify-not-resolve.

## What happened

The dispatched phase leaves for 3-outline and 4-plan moved the plan's phase on their own (phase transition) before the main-context orchestrator ran its Q-Gate for that phase.

## Why it matters

The Q-Gate is meant to run before the phase boundary. When a leaf moves the phase first, the plan sits in the next phase while gate findings for the previous one are still open. This run had 4 such findings in 3-outline and 4 in 4-plan, all of which needed fixing. The ordering guarantee the gate depends on is broken.

## Suggested correction

Phase leaves must return their completion signal and leave the phase transition to the orchestrator, which transitions only after the Q-Gate passes. Enforce this in `plan-marshall:phase-3-outline` / `plan-marshall:phase-4-plan` (or in `manage-status` transition guards that refuse a transition while the phase's gate has not run).

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-004.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
