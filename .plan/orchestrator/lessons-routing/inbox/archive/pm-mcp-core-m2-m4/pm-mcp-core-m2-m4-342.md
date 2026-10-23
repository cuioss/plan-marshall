envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:52Z

component=plan-marshall:persona-code-reviewer
category=improvement
created=2026-10-18

# Give the in-run code review the repository's review path instructions

## Context

In plan-20-job-runner the in-run code review (9 firings) passed four defects that CodeRabbit then raised on PR 92, two of them quoting a rule the repository states in its review path instructions:

- 55ca4f (Major): RuntimeLogMessagesTest checked only a hard-written list of seven records against doc/LogMessages.adoc. CodeRabbit quoted the path instruction "a hardcoded list that must mirror a set defined elsewhere ... unless it is derived from that source at build or run time".
- 06199d: a probe argument check whose predicate always holds on the runner path, quoted against "Check a guard's predicate against the scenario the guard exists for".
- 1e7fe0: JobRecord validated raw JSON members by their first and last characters only, so the builder could produce a record the codec then refuses, and one bad record stops startup recovery for the whole store.
- 4a97d2: awaitReport could block start() for the whole job budget and ignored a cancel.

All four were fixed in TASK-23 and TASK-24, which cost another loop-back.

## Root cause

The code-review leaf reviews against the plan-marshall review rules and the language skills. It does not load the repository's own review rules (the path instructions the review bot is configured with), so rules the project has written down are checked only by the bot, after the PR is open.

## Proposed action

Let the code-review step load the repository's configured review path instructions (for example the path_instructions of the review-bot configuration) as an extra lens, and check each changed file against the rules that match its path. At least the "derived, not hard-written mirror list" and "guard predicate can fire in its scenario" rules should be in the in-run checklist.

## Evidence

- pr-comment 55ca4f, 06199d, 1e7fe0, 4a97d2 (resolution fixed, fix tasks 23 and 24)
- chat_history_analysis loop-back: "Sonar gate C ... plus 86 issues triaged into TASK-21..24"; "CodeRabbit a1a9fe ... (TASK-25)"
