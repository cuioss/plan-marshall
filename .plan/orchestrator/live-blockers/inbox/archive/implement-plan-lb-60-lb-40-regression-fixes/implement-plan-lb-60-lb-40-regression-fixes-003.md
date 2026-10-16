envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T10:37:44Z

component=plan-marshall:manage-tasks
category=anti-pattern
title=Argparse rejection on the manage-tasks read call

# Argparse rejection on the manage-tasks read call

## Context

During plan `implement-plan-lb-60-lb-40-regression-fixes` the
`plan-marshall:manage-tasks:manage-tasks read` verb was invoked once and exited
2 at the argparse boundary with empty stderr. The task read returned nothing and
the caller continued on a missing value.

## Root cause

An argument the verb does not declare (a missing-required or unrecognised
argument at the argparse layer). Note that `read` is the canonical verb and
`get` is its declared alias — the failure is in the argument shape, not the
verb.

## Proposed action

Quote the `read` invocation verbatim from `manage-tasks` Canonical invocations,
and confirm the subcommand's required/optional flags are documented at the call
site that produced the rejection.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:manage-tasks:manage-tasks` subcommand `read`, `exit_code: 2`, subtype `argparse_other`, first at `2026-10-15T21:01:58Z`, occurrence_count 1
