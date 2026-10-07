envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:13:06Z

component=plan-marshall:manage-findings
category=anti-pattern
title=Pass required flags on manage-findings qgate add at execute-exit verify
created=2026-09-16

# Pass required flags on manage-findings qgate add at execute-exit verify

## Context

During plan implement-plan-03-emitter-reenable, the execute-exit verify path invoked `manage-findings qgate add` three times without its required flags. Each call was rejected with exit code 2, and the findings the verify step meant to persist had to be recorded through a fallback path instead.

## Root cause

The caller composed the subcommand from the workflow narrative rather than from the script's declared argparse surface, omitting flags the parser requires.

## Proposed action

Consult `manage-findings qgate add --help` (or the canonical-invocation block) before invoking, and pass every required flag (`--plan-id`, `--phase`, `--source`, `--type`, `--title`, `--detail`).

## Evidence

- aspect: script-failure-analysis — 3 identical exit-2 argparse rejections on notation plan-marshall:manage-findings:manage-findings subcommand qgate at 2026-09-15T21:39:14Z and the two following seconds
- aspect: log-analysis — 8 script errors total on the plan, 3 from this call shape
