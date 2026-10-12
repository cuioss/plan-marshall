envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:13Z

# Candidate lesson: persona augmentation attached java-quarkus and java-cdi skills in a project that forbids Quarkus and CDI

**Signal source**: observation from the plan decision log (4-plan). It is not tied to a gate count, and is forwarded so the orchestrator can classify it.

**Component (suggested)**: `plan-marshall:phase-4-plan` (skill resolution / persona augmentation)

## Evidence

- Decision log 2026-10-10T19:10:20Z: "persona augmentation also adds java-quarkus/java-cdi skills although the project forbids Quarkus and CDI (task descriptions state no Quarkus, no CDI)".
- The project's CLAUDE.md says: "No Quarkus, no CDI: a class that needs a framework type belongs in pm-mcp-server". The pm-mcp-core modules also enforce this through the build (enforcer).

## Why it matters

Execute-time leaves load standards that steer them toward framework patterns the build rejects. The plan only compensated with prose in each task description.

## Suggested direction (for orchestrator classification)

Let persona augmentation honour a project-level skill exclusion, for example a domain or module setting that drops `java-quarkus` / `java-cdi` for pm-mcp-core, instead of relying on task-description prose.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-013.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
