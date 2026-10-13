envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:09Z

# Candidate lesson: phase-4 persona augmentation attached Quarkus/CDI skills to a repository that forbids them

Source: run event in plan verify-not-resolve, phase 4-plan.

## What happened

The phase-4 persona augmentation added Quarkus and CDI skills (for example `pm-dev-java:java-quarkus`, `pm-dev-java:java-cdi`) to tasks in pm-mcp-core. That repository's CLAUDE.md forbids both: "No Quarkus, no CDI", and the build's enforcer rules ban the dependencies.

## Why it matters

Skills that contradict the project's hard constraints push implementation toward patterns the build rejects. They also waste context in every task envelope.

## Suggested correction

Skill and persona augmentation should honour project-level exclusions. Options: a marshal.json / skill-domain exclusion list, or deriving Java framework skills from the module's actual dependencies rather than from the domain alone. Possible home: `plan-marshall:phase-4-plan` skill resolution or `plan-marshall:manage-personas`. In this repository specifically, java-quarkus / java-cdi / junit-weld-testing should never be resolved.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-005.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
