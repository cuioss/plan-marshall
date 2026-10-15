envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T20:35:29Z

# Candidate lesson: Domain detector matched only 'documentation' (alias 'project') for a Java implementation plan

**Component (suggested):** plan-marshall:phase-1-init (domain detection)
**Category (suggested):** bug

## Observation

For plan-17-project-units-and-invariants, a Java implementation plan in the pm-workflow module (new
production classes and JUnit tests), the domain detector returned only `documentation` (via the alias
`project`). The Java domain was not detected, which then fed the later skill and profile choices.

## Root cause (suspected)

The detector appears to weight request vocabulary (work package, specification, ADR wording) over the
affected modules' build system and languages; the alias `project` maps straight to documentation.

## Suggested correction

Derive the domain set from the affected modules' architecture data (build system, source languages) in
addition to the request text, and do not let the `project` alias resolve to documentation alone when the
referenced modules are Java code modules.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-17-project-units-and-invariants-007.md` from plan plan-17-project-units-and-invariants (PLAN-17, #56; harness Claude Code)
