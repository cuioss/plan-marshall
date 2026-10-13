envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:14Z

# Candidate (Q-Gate 3-outline, fixed): outline left an operator question open that an automated execute cannot answer

Source: Q-Gate finding 30f2ef, phase 3-outline, warning; resolution fixed.

## Finding

Risks and Mitigations said the refusal codes other than enrolment_tampered, build_config_changed, path_traversal_rejected and verb_not_supported were "to be confirmed with the operator", while deliverable 2's success criterion already fixed ten codes as a closed set.

## Resolution

The operator confirmed all ten codes, the open-question wording was removed, and deliverable 8 now specifies the codes the Job Runtime specification did not yet name.

## Lesson shape

An outline must not carry an open operator question into execute, because execute cannot ask. Undecided items should be settled at refine/outline time or written into the specification-update deliverable. This applies especially to closed enumerations that a success criterion already depends on.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-011.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
