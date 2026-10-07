envelope_version=1
sender_type=plan
sender_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T16:20:25Z

component=plan-marshall:plan-retrospective
category=bug
title=Fix extract-chat-signal delivering 69 of 288580 reduced transcript bytes

# Fix extract-chat-signal delivering 69 of 288580 reduced transcript bytes

## Context

In the finalize retrospective of the-comment-pipeline-on-the-way-in, `extract-chat-signal run` reported `reduced_bytes: 288580` but `reduced_transcript_delivered_bytes: 69`. The output showed the first transcript line inside the `reduced_transcript: |` block and later transcript lines at column 0 of the document. `over_budget` read `false`, so the aspect selected Tier 1 and analysed a payload it never actually received.

## Root cause

The reduced text reaches the pre-pass as a quoted multi-line value rather than an intact block scalar. This matches the corruption that `chat-history-analysis.md` section "Multi-line serialization" warns about. It happens either in the platform-runtime `chat extract-signal` output or when the pre-pass re-parses it. The delivered figure then measures only the first line.

## Proposed action

Emit the runtime's reduction as a `BlockScalar` end to end, and add a round-trip test on a multi-line transcript that asserts `reduced_transcript_delivered_bytes == reduced_bytes`. When the two figures disagree, route the aspect to a skip that names the gap instead of Tier 1.

## Evidence

- aspect: chat_history_analysis: delivered 69 bytes vs reduced 288580 bytes, 59 operator turns, 20 gate decisions
- aspect: permission_prompt_analysis: prompt population unobservable because of the same truncation
