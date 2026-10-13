envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:13Z

# Candidate (Q-Gate 3-outline, fixed): sibling-repository deliverable declared a module name not in the architecture

Source: Q-Gate finding a4b065, phase 3-outline, warning; resolution fixed.

## Finding

Deliverable 8 declared `module: plan-marshall-documentation`. None of the 21 architecture modules has that name, so phase-4 skill and command resolution by module would find nothing.

## Resolution

Deliverable 8 declares `module: documentation`, as deliverable 7 does, and states that its files live in the sibling repository plan-marshall-documentation, outside this project's architecture.

## Lesson shape

This pairs with the relative-path finding from the same deliverable (c103cb). Cross-repository documentation deliverables have no first-class shape in the outline. A standard form (module, absolute root, PR owner) would prevent both findings.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-010.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
