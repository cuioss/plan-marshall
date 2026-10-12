envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:31:59Z

# Persona-skill union added Quarkus/CDI skills to pm-workflow tasks in a repo that forbids them

Source: decision log 841ac6, 2026-10-11T18:44:42Z.

## What happened

Phase 4 resolved the skills for the Java tasks 2 to 5 (`pm-workflow`) as the union of the domain persona profiles. That union included `pm-dev-java:java-quarkus`, `pm-dev-java:java-cdi`, `pm-dev-java:junit-weld-testing` and `pm-dev-java:junit-integration`. The orchestrator had to remove them by hand: pm-mcp-core's CLAUDE.md says "No Quarkus, no CDI", the build enforcer bans Quarkus/CDI dependencies, and `pm-workflow` has no integration tests.

## Candidate rule / fix

Skill resolution should be narrowed by project facts that are already machine-readable, not only by the domain:
- framework applicability, from the module's actual dependencies (no Quarkus/CDI on the classpath means no Quarkus/CDI/Weld skills);
- the integration-test profile, from whether the module has an integration-tests profile or IT sources.

A project-level exclusion list in marshal.json would also work. Until one of these exists, each Java plan in this repo pays the same manual prune. Owner: plan-marshall `phase-4-plan` skill resolution / `pm-dev-java` profile metadata.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-005.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
