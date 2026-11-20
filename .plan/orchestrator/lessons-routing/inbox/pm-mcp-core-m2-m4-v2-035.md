envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:23Z

component=plan-marshall:workflow-integration-git
category=improvement

# Give finalize inline-fix hand-backs a sanctioned commit path

## Context

In plan-v2-155 the gated `git-workflow commit` refused two inline-fix commits in 6-finalize with `reason: no_sanction` (09:43:20 after the functional-review loop-back, 12:14:37 after the unified triage). Both leaves had made and staged correct edits, but held no composed phase-6 `--step` id, no open loop-back fix task and no section-6 inline-correction record, so each had to hand back and the orchestrator had to commit.

## Root cause

The finalize fix paths that produce inline edits (functional-review correction, wait-region unified triage) are not handed the step id the commit gate requires, so the gate refuses work the workflow itself prescribed.

## Proposed action

Pass the owning phase-6 step id (or an inline-correction record) into every finalize dispatch that is allowed to edit inline, or let the gate accept the loop-back record of the firing step as sanction.

## Evidence

- aspect: script-failure-analysis — `git-workflow commit` script_internal_error, 2 occurrences, reason no_sanction
- aspect: chat-history-analysis — leaf report "Both edits are made and staged, but the gated commit verb refused the commit"
