envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T13:50:31Z

# Do not attach Quarkus/CDI skills to tasks of a repo that forbids them

- component: plan-marshall:phase-4-plan
- category: bug
- source: plan-retrospective (session-log-and-generations, PR #51)

## Context

During 4-plan, task planning resolved skills through the architecture defaults plus the persona resolver
(`persona-implementer`, `persona-module-tester`). That added `pm-dev-java:java-quarkus`, `java-cdi` and
`junit-weld-testing` to every pm-core and pm-runtime task, although the project's CLAUDE.md forbids Quarkus and
CDI in this repository. The plan leaf flagged it, and the operator had to remove the skills at the 4-plan Q-Gate.

## Root cause

Skill resolution for a task follows the domain/profile mapping only. It does not check the project's declared
framework exclusions (here: "No Quarkus, no CDI"), so skills for forbidden frameworks reach the task.

## Proposed action

Let the project declare excluded skills or frameworks (for example in the architecture or domain config) and
filter them out during phase-4-plan skill resolution, or have the persona resolver skip framework skills whose
framework the module does not depend on.

## Evidence

- aspect: chat_history_analysis - operator decision at the 4-plan Q-Gate: "Remove from the tasks (recommended)"
- aspect: chat_history_analysis - 4-plan leaf hand-back: "That adds pm-dev-java:java-quarkus, java-cdi and junit-weld-testing ... although this repository forbids Quarkus and CDI"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `session-log-and-generations-010.md` from plan session-log-and-generations (PLAN-12, #51; Claude Code)
