envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:49:32Z

# Invented flag drift in plan-marshall:manage-architecture:architecture call

## Context

In implement-plan-04-gate-comparability the plan's script-execution log recorded 2 occurrences of an invented flag on architecture find (exit 2, first at 2026-09-11T20:49:23Z).

## Root cause

Caller extrapolated a plausible flag instead of quoting the verbatim argparse surface from the executor mapping or --help output.

## Proposed action

Quote the canonical invocation from the executor mapping or run --help before invoking an unfamiliar manage-* verb; treat exit 2 as an invented-subcommand/flag signal and fix the call site rather than retrying.

## Evidence

- aspect: script_failure_analysis — subtype invented_flag, occurrence_count 2
- component: plan-marshall:manage-architecture:architecture
- category: anti-pattern
- plan: implement-plan-04-gate-comparability
