envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:17Z

# Drop persona skills the project rules exclude from task skill sets

Component: plan-marshall:phase-4-plan
Category (proposed): improvement
Source: plan spend-removal, retrospective (phase-4 author report and both code-review rounds)

## Context

The plan phase resolved task skills from the architecture defaults plus the flattened persona skill sets, using the documented union rule. For the Java tasks of this repository that union added `pm-dev-java:java-quarkus`, `pm-dev-java:java-cdi` and `pm-dev-java:junit-weld-testing`, although the repository's CLAUDE.md states "No Quarkus, no CDI" for every module. The phase-4 author flagged the conflict itself; both code-review authors then listed these sources and skipped them as "ruled out by CLAUDE.md".

## Root cause

The persona union is computed from the persona definitions alone; nothing filters it against project-level exclusions, so every Java task carries skills that contradict the project's code rules, and each consumer must notice and discard them on its own.

## Proposed action

- Give the project an explicit skill exclusion list (for example in marshal.json, or derived from the architecture profile) that phase-4 applies after the persona union, and log each dropped skill.
- Until then, have phase-4 record the conflict as a decision so reviewers do not have to rediscover it.

## Evidence

- aspect: chat_history_analysis - phase-4 author: "This adds java-quarkus, java-cdi and junit-weld-testing to the Java tasks, which this repository's CLAUDE.md rules out for the code itself."
- aspect: chat_history_analysis - code review round 2: "pm-dev-java:java-quarkus and pm-dev-java:java-cdi: ruled out by CLAUDE.md" (recorded under rule_sources_not_loaded).
