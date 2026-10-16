envelope_version=1
sender_type=plan
sender_id=lb-26-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T19:09:36Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
title=Show router-scoped plan-id placement on the ci invocation block

# Show router-scoped plan-id placement on the ci invocation block

## Context

The lb-26-regression-fixes run recorded an argparse rejection on plan-marshall:tools-integration-ci:ci --plan-id from placing a router-scoped flag after the verb. CI still finished green and PR 1778 merged via the queue.

## Root cause

The ci router consumes --plan-id before the verb while body-consumer verbs require it after, and the invocation block does not show the placement side by side.

## Proposed action

Show the pre-verb and post-verb --plan-id forms in one canonical example in the ci skill docs.

## Evidence

- aspect: script-failure-analysis — argparse_other on tools-integration-ci:ci --plan-id
- aspect: manifest-decisions — branch-cleanup paired with 27 changed files, all checks consistent
