envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:15:38Z

# Router-scoped --plan-id placement drift across ci/build_server/platform_runtime calls

## Context

The plan-07-session-identity run recorded 4 exit-2 argparse rejections sharing one shape: a router-scoped flag appended after the verb (ci checks --plan-id, build_server preflight --plan-id, platform_runtime runtime-info --plan-id). Each was retried in-band and none blocked the run.

## Root cause

Callers guess the flag position; the ci note already states the placement rule (router flag before the verb) but nothing enforces it at dispatch time.

## Proposed action

Consider a pre-dispatch argparse dry-run validator that rejects a misplaced router-scoped flag before execution, or a single documented placement table for router-flag scripts.

## Evidence

- aspect: script-failure-analysis — 4 invented_flag/argparse_other rows with unrecognized arguments: --plan-id after the verb
- plan: plan-07-session-identity, PR #1530
