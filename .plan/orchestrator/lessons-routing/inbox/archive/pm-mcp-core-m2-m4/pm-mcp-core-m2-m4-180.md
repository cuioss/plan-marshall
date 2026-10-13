envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:16Z

# Candidate (Q-Gate 4-plan, accepted): test/impl module mismatch for a Javadoc-only cross-module step

Source: Q-Gate finding adaecb, phase 4-plan, module_mapping_validator for deliverable 4; resolution accepted.

## Finding

The module_testing task TASK-8 (ArgumentCheckTest, module pm-runtime) pairs with TASK-7, which also touches `pm-core/src/main/java/de/planmarshall/core/store/ProjectEnrolment.java` (module pm-core). `doc/developer/test-impl-mapping.adoc` does not exist, so no row covers the pair.

## Resolution

Accepted: the ProjectEnrolment.java step is Javadoc only, so no test mapping is needed.

## Lesson shape

module_mapping_validator flags documentation-only steps in another module as test/impl mismatches. The validator could skip steps marked Javadoc-only or documentation-only. Alternatively, the repository could add a test-impl-mapping document so these pairs have a place to be recorded.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-015.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
