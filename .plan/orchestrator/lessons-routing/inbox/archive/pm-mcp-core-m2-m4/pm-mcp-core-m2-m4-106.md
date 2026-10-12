envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:47Z

# Phase leaves advance their own phase status, so an operator-requested fix pass needs a manual set-phase re-open

## Observation

The refine, outline and plan leaves transitioned the plan's phase status themselves on return. After the 3-outline Q-Gate left four findings, the plan had already moved to 4-plan, so the orchestrator had to re-open 3-outline with `set-phase` (4-plan -> 3-outline) before it could dispatch the operator-requested outline fix pass, and then rely on the loop-back re-entry marker to reconcile the handshake.

## Suggested direction

Let the main-context orchestrator own phase transitions at the boundaries where it still runs a gate after the leaf returns (q-gate-validation, operator review): the leaf reports completion, and the orchestrator advances the phase only once the post-return gate has passed. That removes the backwards set-phase and the loop-back re-entry machinery from the normal fix-pass path.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-017.md` from plan runtime-lifecycle (PLAN-08, #29)
