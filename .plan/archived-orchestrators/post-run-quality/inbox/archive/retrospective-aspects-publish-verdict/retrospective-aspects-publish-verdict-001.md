envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:25:23Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
title=Indent every line of a BlockScalar body, not only the first

# Indent every line of a BlockScalar body, not only the first

## Context

PLAN-PRQ-02 D3 set out to make `extract-chat-signal`'s `reduced_transcript` survive its
own serialization. On this plan's OWN retrospective run, immediately after the plan
landed, the pre-pass reported `reduced_bytes: 725532` and
`reduced_transcript_delivered_bytes: 69` — 0.01% of the reduction reached the consumer.

Inspecting the emitted document shows why: `reduced_transcript: |` is followed by ONE
body line indented two spaces, and every subsequent line at column 0. `parse_toon`
terminates the block scalar at the first flush-left line and re-reads the remainder as
sibling top-level keys. Phantom keys observable in that very output include
`<command-name>/plan-marshall`, `operator-decision` and `user`.

This is the third independent report of this defect shape (the original lesson, D3
itself, and now this run).

## Root cause

The block-scalar emission path indents the header and the first body line but does not
re-indent the remaining lines of a multi-line value. The producer/serializer boundary
contract (`ref-toon-format/scripts/toon_parser.py` `BlockScalar`) states the body is
"indented two spaces past the header" so that it round-trips verbatim; the emitted
document does not satisfy that for lines 2..N.

## Proposed action

Fix the block-scalar writer so EVERY line of the body carries the two-space indent, and
add a round-trip test whose fixture body is multi-line AND contains a colon on a
non-first line — the single-line and first-line-only cases both pass today and are why
this shipped. Assert on the parsed round-trip, not on the serialized string.

Then re-check the consumer: with the producer fixed,
`reduced_transcript_delivered_bytes` should equal `reduced_bytes`.

## Evidence

- aspect: chat_history_analysis — `reduced_bytes: 725532` vs `reduced_transcript_delivered_bytes: 69`, `round_tripped: false`
- aspect: permission_prompt_analysis — 121 of 123 operator turns and 7 of 7 gate-decision bodies never delivered
- artifact: `.plan/local/plans/retrospective-aspects-publish-verdict/work/chat-signal-prepass.toon` lines 7-19 show the indent breaking after line 1
- prior art: spec D3 and folded inbox message `prq-06-a-lane-override-that-cannot-take-effect-is-002.md`
