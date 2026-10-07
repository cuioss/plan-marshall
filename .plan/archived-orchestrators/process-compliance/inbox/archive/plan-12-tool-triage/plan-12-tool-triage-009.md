envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=candidate-lesson
created=2026-09-29T13:39:30Z

component=plan-marshall:plan-retrospective
category=bug

# Route chat-history to Tier 2 when delivered bytes fall far short of reduced

## Context

In plan-12-tool-triage the chat-history pre-pass (`extract-chat-signal run`) reported `reduced_bytes: 494807` but `reduced_transcript_delivered_bytes: 69`, with `operator_turn_count: 125` and `gate_decision_count: 26`. Because `no_signal` and `over_budget` were both false, the aspect ran as Tier 1 on a 69-byte input: 1 of 26 gate decisions was readable and no operator turn was. The pre-pass stdout also carried payload lines flush-left at column 0, the corruption shape `chat-history-analysis.md` § Multi-line serialization warns about. The permission-prompt aspect, which reads the same transcript, could not look either.

## Root cause

The tier gate reads only `no_signal` / `over_budget`. It never compares the delivered figure with the produced one, so a payload lost between the runtime op and the pre-pass selects full analysis over almost nothing. Where the bytes are lost (runtime op emission vs pre-pass parse) was not established.

## Proposed action

Treat a large delivered-vs-reduced gap as a Tier-2 skip with a distinct reason, or as an error, instead of Tier 1. Find which side of the `chat extract-signal` → `extract-chat-signal` boundary drops the multi-line reduction and emit it as a `BlockScalar`. Add a regression test that feeds a multi-line reduction through the boundary and asserts delivered == reduced.

## Evidence

- aspect: chat_history_analysis — reduced_bytes=494807, reduced_transcript_delivered_bytes=69, over_budget=false, no_signal=false (session bf78eae8-48cc-4369-ac15-823fb9dfab66)
- aspect: permission_prompt_analysis — coverage unmeasured for the same reason
