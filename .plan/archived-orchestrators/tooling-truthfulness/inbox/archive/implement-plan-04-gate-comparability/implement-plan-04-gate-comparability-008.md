envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:50:06Z

# Argparse rejection in plan-marshall:plan-retrospective:check-artifact-consistency call

## Context

In implement-plan-04-gate-comparability the retrospective step recorded 1 argparse rejection on check-artifact-consistency run with an undeclared flag set (exit 2, at 2026-09-12T10:42:03Z).

## Root cause

Caller used a flag outside the declared run surface (archived-plan-path, mode, plan-id) instead of the canonical invocation.

## Proposed action

Use only the canonical check-artifact-consistency run flags and pre-check with --help; treat exit 2 as an invented-flag signal.

## Evidence

- aspect: script_failure_analysis — subtype argparse_other, occurrence_count 1
- component: plan-marshall:plan-retrospective:check-artifact-consistency
- category: anti-pattern
- plan: implement-plan-04-gate-comparability
