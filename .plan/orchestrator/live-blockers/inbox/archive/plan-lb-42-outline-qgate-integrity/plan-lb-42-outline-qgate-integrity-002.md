envelope_version=1
sender_type=plan
sender_id=plan-lb-42-outline-qgate-integrity
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T11:36:41Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
title=Verify manage-* subcommand flags via --help before invoking
source_plan=plan-lb-42-outline-qgate-integrity
confidence=high

# Verify manage-* subcommand flags via --help before invoking

## Context

The plan-lb-42-outline-qgate-integrity retrospective recorded 20 argparse rejections across 11 unique manage-* invocations (invented verbs such as manage-files list and manage-logging read, invented flags on architecture resolve and manage-change-ledger query). Each rejection bypassed the script body and left no partial state, and all 20 were recovered inline during exploration.

## Root cause

Workflow prose names verbs that read like the script's argparse surface but are not it; without a --help check the call is issued on narrative plausibility rather than the declared choices.

## Proposed action

Before issuing a manage-* call whose subcommand or flags were not copied verbatim from a canonical-invocation block, run the script with --help first and quote the declared verb and flags exactly.

## Evidence

- aspect: script_failure_analysis — 11 unique argparse rejections, 20 total, all exit_code 2
- aspect: log-analysis — errors_script 20 corroborate the same population
