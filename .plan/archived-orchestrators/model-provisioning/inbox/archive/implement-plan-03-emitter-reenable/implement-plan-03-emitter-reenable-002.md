envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:13:20Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
title=Check --help before invoking manage-* verbs with guessed flags
created=2026-09-16

# Check --help before invoking manage-* verbs with guessed flags

## Context

During plan implement-plan-03-emitter-reenable, callers across three phases hit eight argparse rejections (exit code 2) over five unique invented verb/flag shapes on four components: `manage-config get` (twice), `manage-findings qgate` without required flags (three times), `manage-references get` without `--field`, `manage-config coverage` with an undeclared `--plan-id`, and `manage-execution-manifest show`.

## Root cause

Callers extrapolated plausible-sounding verbs and flags from workflow prose instead of quoting the script's declared argparse surface, so the calls bypassed the script body and left the intended work undone or retried.

## Proposed action

Reinforce the never-invent-subcommands rule: run the script with `--help` first (or quote the canonical-invocation block) whenever the verb or flag set is not already confirmed, especially after crossing into a new component.

## Evidence

- aspect: script-failure-analysis — total_failures 8, unique_failures 5, across plan-marshall:manage-config, plan-marshall:manage-findings, plan-marshall:manage-references, plan-marshall:manage-execution-manifest
- aspect: log-analysis — 8 work-log ERROR entries pairing 1:1 with the script failures
