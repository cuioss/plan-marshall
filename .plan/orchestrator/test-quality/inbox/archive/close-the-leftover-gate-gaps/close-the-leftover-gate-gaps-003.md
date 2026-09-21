envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:04:26Z

component=plan-marshall:phase-5-execute
category=anti-pattern
title=Stop retrying an invented manage-* verb after its first argparse rejection

# Stop retrying an invented manage-* verb after its first argparse rejection

## Context

In plan close-the-leftover-gate-gaps, script-execution.log holds 22 failures across 12 unique signatures. Two invented verbs were retried without consulting --help: manage-tasks view (6 occurrences) and manage-status phase-handshake (4 occurrences). Every retry exited 2 with the same rejection.

## Root cause

The agent treated exit-2 as a transient failure and re-issued the identical invented subcommand instead of reading the script's --help (or the canonical-forms table) after the first rejection.

## Proposed action

After any exit-2 argparse rejection, resolve the verb from --help output before retrying; never re-issue the identical rejected argv. Consider a one-line guard in the executing workflow: first rejection → help lookup, not retry.

## Evidence

- aspect: script_failure_analysis — manage-tasks view x6, manage-status phase-handshake x4, all exit 2
- aspect: script_failure_analysis — manage-findings resolve with prose args (invented_flag), ci --plan-id misplacement
