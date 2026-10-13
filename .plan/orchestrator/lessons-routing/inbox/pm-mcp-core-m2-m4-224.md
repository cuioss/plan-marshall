envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:09Z

# Filter persona-merged task skills by the module's real frameworks

Component: plan-marshall:phase-4-plan (category: improvement, confidence: high)

## Context

phase-4-plan merged the persona skills into TASK-2..4 of scenario-replay-harness as its spec requires, which added
`pm-dev-java:java-quarkus`, `pm-dev-java:junit-weld-testing` and `pm-dev-java:junit-integration`. The module,
`pm-workflow`, is plain Java with no Quarkus and no CDI (the project forbids both outside `pm-mcp-server`). The 4-plan
leaf flagged it and the 5-execute leaf was told to skip loading those skills.

## Root cause

The persona-skill merge is applied per domain without checking the target module's dependencies or frameworks.

## Proposed action

Filter merged framework skills against the module's architecture data (dependencies / frameworks from
manage-architecture), or drop framework-specific skills when the module does not declare the framework.

## Evidence

- 4-plan hand-back: "adds java-quarkus, junit-weld-testing and junit-integration ... pm-workflow is plain Java"
- 5-execute hand-back: "As instructed, I did not load java-quarkus, junit-weld-testing or junit-integration"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-015.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
