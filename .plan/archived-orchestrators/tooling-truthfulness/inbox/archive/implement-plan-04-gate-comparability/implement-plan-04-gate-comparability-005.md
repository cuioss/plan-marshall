envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:49:43Z

# Argparse rejection in plan-marshall:manage-solution-outline:manage-solution-outline call

## Context

In implement-plan-04-gate-comparability the plan's script-execution log recorded 1 argparse rejection on manage-solution-outline get-deliverable (exit 2, first at 2026-09-11T21:20:37Z).

## Root cause

Caller used an undeclared flag for get-deliverable instead of the declared surface (deliverable-number, plan-id).

## Proposed action

Use only the declared flags for manage-solution-outline get-deliverable and pre-check with --help when unsure; treat exit 2 as an invented-flag signal.

## Evidence

- aspect: script_failure_analysis — subtype argparse_other, occurrence_count 1
- component: plan-marshall:manage-solution-outline:manage-solution-outline
- category: anti-pattern
- plan: implement-plan-04-gate-comparability
