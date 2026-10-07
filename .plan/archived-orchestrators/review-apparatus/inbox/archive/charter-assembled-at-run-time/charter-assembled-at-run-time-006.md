envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:12:25Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
confidence=high

# Align self_review's base freshness check with sync-baseline's base

## Context

In plan `charter-assembled-at-run-time`, `finalize-step-sync-baseline` completed with "already contains origin/main (behind 0)". Minutes later, `ext-self-review-plan-marshall:self_review surface` exited 1 twice (05:58Z and 06:13Z) with "local base 'main' sits behind 'origin/main' - refusing to surface a stale scope". The first refusal ended its dispatch as an `error` boundary row costing 145,177 tokens, and the step recorded `failed` before the loop-back chain began.

## Root cause

The two steps compare different refs: sync-baseline checks the worktree HEAD against `origin/main`, while self_review checks the local `main` ref against `origin/main`. A stale local `main` in the main checkout therefore passes the first check and fails the second, and nothing in between advances it.

## Proposed action

Make self_review compute its scope base from `origin/{base}` (the ref sync-baseline already verified), or have sync-baseline fast-forward the local base ref when it is strictly behind. Either way, the two steps should read one base. Add a test where local `main` is behind `origin/main` but the branch already contains `origin/main`: self_review must surface normally.

## Evidence

- aspect: script_failure_analysis: 2x script_internal_error in self_review (stale local base)
- aspect: logging_gap_analysis / log_analysis: 6-finalize error row 145,177 tokens
- status.json: finalize-step-sync-baseline "already contains origin/main (behind 0)"
