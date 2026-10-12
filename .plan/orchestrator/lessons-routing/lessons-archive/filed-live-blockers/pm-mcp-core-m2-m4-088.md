envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:33Z

# Candidate lesson: phase-4 persona augmentation attaches forbidden framework skills and misses cui-testing

Component: plan-marshall:phase-4-plan (persona/skill augmentation)
Category (proposed): bug
Source: plan code-analysis-base, phase-4-plan task skills

## Observation

The persona augmentation in phase-4-plan attached `pm-dev-java:java-quarkus`, `pm-dev-java:java-cdi` and `pm-dev-java:junit-weld-testing` to tasks in pm-mcp-core, a repository whose CLAUDE.md and enforcer rules forbid Quarkus and CDI in every module. At the same time it did not attach `pm-dev-java-cui:cui-testing`, which the project's test rules require (cui-test-generator, cui-test-juli-logger). The augmentation selects by the Java domain profile alone and ignores what the module actually depends on.

## Proposed correction

Derive the augmented skills from the module's real dependencies (architecture inventory: a Quarkus/CDI/Weld skill only when the module depends on it; cui-testing when the module's test scope uses cui-test-generator or cui-test-juli-logger), or let the project declare an exclude/include list in marshal.json that the augmentation honours.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-006.md` from plan code-analysis-base (PLAN-36, #31)
