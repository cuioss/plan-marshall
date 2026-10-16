envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T10:37:44Z

component=plan-marshall:manage-status
category=bug
title=Script-internal error in the manage-status transition call

# Script-internal error in the manage-status transition call

## Context

During plan `implement-plan-lb-60-lb-40-regression-fixes` the
`plan-marshall:manage-status:manage-status transition` verb exited 1 twice with
a non-argparse, script-internal failure. Both failures are inside the script
body rather than at the argument boundary, so they are defects in
`manage-status` itself rather than caller drift.

## Root cause

Unknown from the plan logs alone — the recorded excerpt is empty. A non-argparse
exit 1 from this verb means the transition handler raised.

## Proposed action

Reproduce `manage-status transition` on the transition that was in flight
(`2026-10-15T22:31:46Z`) and fix the raising path; the two occurrences 200s
apart suggest a repeatable condition rather than a one-off.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:manage-status:manage-status` subcommand `transition`, `exit_code: 1`, subtype `script_internal_error`, first at `2026-10-15T22:31:46Z`, occurrence_count 2
