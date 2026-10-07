envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:50:00Z

# Argparse rejection in plan-marshall:tools-integration-ci:ci call

## Context

In implement-plan-04-gate-comparability the finalize run recorded 1 argparse rejection on ci pr landing-state with an undeclared branch flag (exit 2, at 2026-09-12T10:09:52Z).

## Root cause

Caller extrapolated a plausible flag for the ci verb instead of using the declared flag set from --help or the executor mapping.

## Proposed action

Run ci --help or consult the executor mapping before invoking ci verbs; use only declared flags and treat exit 2 as an invented-flag signal.

## Evidence

- aspect: script_failure_analysis — subtype argparse_other, occurrence_count 1
- component: plan-marshall:tools-integration-ci:ci
- category: anti-pattern
- plan: implement-plan-04-gate-comparability
