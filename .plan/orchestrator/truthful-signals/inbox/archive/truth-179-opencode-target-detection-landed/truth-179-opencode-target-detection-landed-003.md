envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=truthful-signals
kind=candidate-lesson
created=2026-09-25T13:22:26Z

# Fix manage-config effort internal error (5 hits this plan)

## Context

During plan truth-179-opencode-target-detection-landed the manage-config
effort subcommand raised a script-internal error (exit 1) 5 times, first at
2026-09-24T05:28:25Z. The recorded traceback shows a failed import inside
manage-config.py (from _cmd_finalize... module import). The plan recovered and
landed via PR #1619.

## Root cause

A broken or misnamed import on the effort code path of manage-config; the
failing import line is captured in the traceback in logs/script-execution.log
at the first timestamp.

## Proposed action

Fix the _cmd_finalize import in
marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py
so the effort subcommand imports cleanly, with a regression test invoking it.

## Evidence

- aspect: script_failure_analysis — 5 occurrences of script_internal_error in plan-marshall:manage-config:manage-config effort, exit_code 1, traceback naming the _cmd_finalize import
- plan: truth-179-opencode-target-detection-landed (orchestrated, epic truthful-signals)

component: plan-marshall:manage-config
category: bug
confidence: medium
