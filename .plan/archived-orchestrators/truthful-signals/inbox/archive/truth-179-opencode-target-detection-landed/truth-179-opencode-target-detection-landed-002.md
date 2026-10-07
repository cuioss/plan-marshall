envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=truthful-signals
kind=candidate-lesson
created=2026-09-25T13:22:12Z

# Fix scope_creep_check internal error (7 hits this plan)

## Context

During plan truth-179-opencode-target-detection-landed the phase-5-execute
scope_creep_check subcommand raised a script-internal error (exit 1) 7 times,
first at 2026-09-24T08:33:59Z. The plan recovered and landed via PR #1619, so
the failures were retried or routed around rather than fixed.

## Root cause

Unknown. The scope-creep check fails internally under conditions this plan hit
repeatedly at execute-phase entry; triage starts from the script log around
the first timestamp.

## Proposed action

Reproduce the scope_creep_check sequence from logs/script-execution.log around
2026-09-24T08:33:59Z and fix the internal error in the check handler.

## Evidence

- aspect: script_failure_analysis — 7 occurrences of script_internal_error in plan-marshall:phase-5-execute:scope_creep_check check, exit_code 1
- plan: truth-179-opencode-target-detection-landed (orchestrated, epic truthful-signals)

component: plan-marshall:phase-5-execute
category: bug
confidence: medium
