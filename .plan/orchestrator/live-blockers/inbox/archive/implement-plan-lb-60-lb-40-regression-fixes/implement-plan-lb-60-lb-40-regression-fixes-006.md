envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T10:37:44Z

component=plan-marshall:manage-change-ledger
category=anti-pattern
title=Invented flag drift in the manage-change-ledger query call

# Invented flag drift in the manage-change-ledger query call

## Context

During plan `implement-plan-lb-60-lb-40-regression-fixes` the
`plan-marshall:manage-change-ledger:manage-change-ledger query` verb was invoked
once with an undeclared flag. Argparse rejected the call (`unrecognized
argument`) and exited 2, so the ledger query never ran.

## Root cause

The flag was paraphrased from workflow prose rather than quoted from the verb's
declared argparse surface — the same `argparse_rejection` recurrence class as
the sibling architecture-search occurrence in this plan.

## Proposed action

Quote the `query` subcommand's flags verbatim from the script's Canonical
invocations block; add the canonical `query` invocation to
`manage-change-ledger`'s Canonical invocations section if it is missing, so
callers copy an exact shape instead of inventing one.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:manage-change-ledger:manage-change-ledger` subcommand `query`, `exit_code: 2`, subtype `invented_flag`, first at `2026-10-15T20:43:14Z`, occurrence_count 1
