envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:41Z

# Candidate lesson: Persona augmentation must honour project framework exclusions

Source: plan-retrospective (chat-history-analysis: 4-plan return + both code-review rounds), plan-69-unit-frontmatter-and-types
Component (suggested): plan-marshall:phase-4-plan (foreign bundle - route to plan-marshall lessons inbox)
Category (suggested): improvement

## Context

In 4-plan the mandatory persona augmentation added `pm-dev-java:java-quarkus`, `java-cdi` and `junit-weld-testing` to every Java task, although this repository's CLAUDE.md states "No Quarkus, no CDI" and the build enforcer forbids those dependencies. The planner flagged it but followed the workflow; every later code-review and functional-review dispatch then had to be told to skip those rule sources.

## Root cause

Augmentation selects skills from the domain's profile alone and has no input for project-declared exclusions, so a framework the project forbids is loaded into every task context.

## Proposed action

Give the java domain (or the project config) an exclusion list of skills that augmentation must not add - e.g. a `marshal.json` per-project skill deny list - and have phase-4-plan apply it, logging each dropped skill as a decision.

## Evidence

- 4-plan return note 2: "Persona augmentation ... added java-quarkus, java-cdi and junit-weld-testing ... CLAUDE.md says this repository uses no Quarkus or CDI"
- code-review rounds 1 and 3: "Skipped rule sources: java-quarkus, java-cdi and junit-weld-testing"
