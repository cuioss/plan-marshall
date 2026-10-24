---
description: The runbook lane - implementation contract for ONE staged orchestrator plan spec on a cheap model, without the /plan-marshall lifecycle. Resolves every project-specific value (epic slug, derived names, build commands, reviewers with their trigger comments, commit trailer, inbox command) through the runbook_lane resolve verb, then runs the lane - progress file and resume, hard rules, evidence orders (test-first, mutation-after, none), build gate, self-review rounds, PR and review cycle, merge gate, cleanup, and a landing message to the epic inbox - from any project that has plan-marshall installed
---

Load and run the `plan-marshall-runbook-lane` skill instructions, then carry out its instructions using the user input below.

User input:

$ARGUMENTS
