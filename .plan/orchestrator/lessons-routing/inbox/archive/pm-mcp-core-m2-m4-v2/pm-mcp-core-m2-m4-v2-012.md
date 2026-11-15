envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T23:11:04Z

component=plan-marshall:automatic-review
category=bug
title=Pass an explicit timeout on the 180 s wait-for-comments call
confidence=medium

# Pass an explicit timeout on the 180 s wait-for-comments call

## Context

In the second automatic-review firing of plan-v2-57-default-plan-lanes-and-run (PR 378, HEAD 614e8e51), the leaf reported that "the 180 s wait-for-comments call was moved to the background by the host and ended with timed_out: true, new_count: 0". The step still completed correctly, but the wait was result-bearing and ran inside a dispatched leaf.

## Root cause

The 180 s buffer plus overhead exceeds the host's default 2-minute Bash timeout. When the workflow does not tell the leaf to pass an explicit `timeout`, the host moves the call to the background. That breaks the "synchronous Bash is the wait" rule for leaves.

## Proposed action

In the automatic-review workflow, state the Bash `timeout` for the `ci pr wait-for-comments` call (buffer seconds plus margin, in ms, capped at the seam-resolved ceiling), the same way build calls carry `bash_timeout_seconds`.

## Evidence

- chat_history_analysis: automatic-review iteration 2 hand-back, "Completion polls" bullet
- manifest: review_bot_buffer_seconds 180
