envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:59Z

# Candidate lesson: Framework skills were attached to tasks in a module the build forbids from using that framework

- Component: plan-marshall:phase-4-plan
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-018 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during plan primitive-spi-and-validators. Checked against the task records of the plan.

## What happened

The automatic skill selection attached Quarkus and CDI skills to tasks in `pm-core`. The enforcer rules of the root POM fail the build when any module of this repository depends on Quarkus, CDI, Vert.x or an MCP library. The task author had to write a counter-instruction into the task text: "pm-core is plain Java; ignore any loaded framework skill (Quarkus, CDI, Weld)."

## Verification of the wording

- Confirmed for Quarkus and CDI: TASK-2 (domain java, profile implementation, origin plan) lists `pm-dev-java:java-quarkus` and `pm-dev-java:java-cdi` among its 11 skills, and its description carries the counter-instruction quoted above.
- NOT confirmed for Weld: TASK-2 lists no Weld skill. Weld is named only in the counter-instruction. The test tasks, where a Weld testing skill would be attached, were not read by this step.
- Contrast: TASK-10 (origin fix, created by the finalize triage) lists 5 skills and neither framework skill, so the triage-created tasks did not have the problem.
- Related: the domain detection at init reports "over_provisioned_resolve (zero narrative match, all offerable domains provisioned)" (decision log 4e5623).

## Proposed rule

Skill selection for a task takes the dependency rules of the target module into account: a skill for a framework the module may not depend on is not attached. Where that cannot be derived, the project can declare per module which skills are excluded, so the exclusion is configuration and not a sentence repeated in every task text.

## Evidence

- `manage-tasks read` of TASK-2 and TASK-10.
- Decision log 4e5623.
- Project instructions of pm-mcp-core, "Dependency Rules (enforced by the build)".
