envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:49:53Z

# Invented flag drift in plan-marshall:workflow-integration-github:github_pr call

## Context

In implement-plan-04-gate-comparability the automatic-review step recorded 1 argparse rejection on github_pr bot_completion with an unrecognized --plan-id argument (exit 2, at 2026-09-12T10:07:13Z).

## Root cause

Caller appended a router-scoped --plan-id after a verb that declares no such flag, instead of consulting the verb's canonical invocation.

## Proposed action

Consult the github_pr canonical invocation before adding --plan-id; verbs that declare no --plan-id take none, and a pre-verb router flag must not be placed after the verb.

## Evidence

- aspect: script_failure_analysis — subtype invented_flag, occurrence_count 1
- component: plan-marshall:workflow-integration-github:github_pr
- category: anti-pattern
- plan: implement-plan-04-gate-comparability
