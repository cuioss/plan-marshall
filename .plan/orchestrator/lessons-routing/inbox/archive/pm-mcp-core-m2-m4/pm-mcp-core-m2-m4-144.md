envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T18:33:32Z

# Proposed lesson: read --help before invoking unfamiliar manage-* subcommands

Component: plan-marshall:persona-plan-marshall-agent
Category: anti-pattern
Confidence: high

## Context

PLAN-44 logged 12 argparse-rejection clusters across 9 script notations (invented subcommands such as manage-status show and invented flags such as --plan-id on platform_runtime harness). Every one recovered on retry, but each cost a round trip.

## Root cause

Callers extrapolated verb and flag names from workflow prose instead of quoting them verbatim from the executor mapping or --help output.

## Proposed action

Keep enforcing the never-invent-subcommands rule and the --help-first habit in every workflow that issues manage-* calls; treat an exit-2 rejection as a stop-and-read signal, never as a shape to route around.

## Evidence

- aspect: script-failure-analysis — 12 failures, 9 argparse_other and 3 invented_flag
- aspect: logging-gap-analysis — 12 script-execution errors plus 12 work-log errors from the same drift

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-44-static-verifier-rule-gaps-003.md` from plan plan-44-static-verifier-rule-gaps (PLAN-44, #38; opencode)
