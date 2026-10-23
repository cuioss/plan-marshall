envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:34Z

component=plan-marshall:phase-4-plan
category=bug
confidence=high
source=plan-retrospective (chat-history-analysis, request-result-alignment); phase-4-plan hand-back 2026-10-17T15:35Z

# Do not attach framework skills the project CLAUDE.md forbids to tasks

## Context

Phase 4-plan's persona augmentation gave every Java task of plan-74-credential-store-choice `pm-dev-java:java-quarkus` and `pm-dev-java:java-cdi` (and `junit-weld-testing` on test tasks). This repository's CLAUDE.md forbids Quarkus and CDI in every module. The plan agent flagged it, and every later code-review author had to state that it "cited nothing from java-quarkus, java-cdi or junit-weld-testing", while still loading them into each envelope.

## Root cause

The persona resolver widens task skills from the domain profile without filtering against the project's declared framework prohibitions, so forbidden-framework standards ride into every execute and review envelope.

## Proposed action

Filter persona-augmented skills against a project-level exclusion (marshal.json skill-domain config or a declared prohibition list) at plan time, and log what was excluded, so execute and review envelopes never load standards the project forbids.

## Evidence

- phase-4-plan hand-back: "the Java tasks also received java-quarkus and java-cdi (and junit-weld-testing on test tasks) from the persona resolver. This repository forbids Quarkus and CDI."
- code-review hand-backs (rounds 1-7): "I cited nothing from java-quarkus, java-cdi or junit-weld-testing"
