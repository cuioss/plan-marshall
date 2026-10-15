envelope_version=1
sender_type=plan
sender_id=antigravity-execution-fidelity
epic=live-blockers
kind=candidate-lesson
created=2026-10-14T21:31:45Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
title=ci checks rejects post-verb --plan-id placement

# ci checks rejects post-verb --plan-id placement

## Context

During antigravity-execution-fidelity, a call to the `ci` router as
`ci checks --plan-id ...` was rejected with exit code 2: `--plan-id` is a
top-level router flag consumed before the subcommand verb, so placing it after
a read verb that declares no `--plan-id` of its own is an argparse rejection.

## Root cause

Callers append `--plan-id` by rote after the verb instead of consulting the
script's canonical-invocation block for the position its parser requires.

## Proposed action

Make the ci read-verb call sites place `--plan-id` before the verb, and keep
the per-script flag-position rule visible where ci invocations are authored.

## Evidence

- aspect: script-failure-analysis — invented_flag on ci checks with stderr naming the top-level-flag-before-verb rule
- confidence: medium; source plan: antigravity-execution-fidelity
