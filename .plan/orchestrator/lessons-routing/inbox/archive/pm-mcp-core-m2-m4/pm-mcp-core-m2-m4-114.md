envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:51Z

# Persona skill augmentation attaches Quarkus/CDI skills to tasks in a repository that forbids them

## Observation

Phase 4's persona augmentation added `pm-dev-java:java-quarkus`, `pm-dev-java:java-cdi` and `pm-dev-java:junit-weld-testing` to every Java task. pm-mcp-core's modules are plain Java and the build enforcer forbids Quarkus/CDI dependencies. The planner could only leave a free-text note asking the executor to ignore them, so each execute envelope loaded irrelevant standards (token cost) and risked steering code toward forbidden patterns.

## Suggested direction

Filter persona-augmented skills by the module's actual dependencies (architecture inventory: does the module depend on quarkus / jakarta.enterprise / weld?) or by a project-level skill exclusion in marshal.json, rather than attaching the full Java persona set unconditionally.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-025.md` from plan runtime-lifecycle (PLAN-08, #29)
