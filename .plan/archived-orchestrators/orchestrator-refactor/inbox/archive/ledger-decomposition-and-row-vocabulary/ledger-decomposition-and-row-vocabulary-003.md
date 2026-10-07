envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:04:27Z

# Emit extract-chat-signal reduced_transcript as an indented block scalar

component: plan-marshall:plan-retrospective
category: bug

## Context

The retrospective of ledger-decomposition-and-row-vocabulary ran `extract-chat-signal run --session-id 7f2f3f24-16cc-4808-b0db-479ef11e00e9`. The result reported `reduced_bytes: 209481` but `reduced_transcript_delivered_bytes: 69`. Only the first line of `reduced_transcript` was indented under its `key: |` header; every other line reached column 0. Of 45 operator turns and 9 gate decisions, only the merge-queue go-ahead and one subagent hand-back frame were readable.

## Root cause

The producer does not wrap the reduced text as `BlockScalar` (or the value arrives pre-quoted with raw newlines), so `serialize_toon` quotes it without indenting its continuation lines. That breaks the chat-history-analysis contract rule that no line of a multi-line value may reach column 0. Because `over_budget` is derived from the delivered bytes (69), the budget check always passes, and Tier 1 is selected with a one-line input.

## Proposed action

Mark `reduced_transcript` as `BlockScalar` before serialising it. Add a round-trip test in which a multi-line transcript's delivered bytes equal `reduced_bytes`. Treat `delivered << reduced` as a Tier-2 degradation, not as Tier 1.

## Evidence

- aspect: chat_history_analysis — reduced_bytes=209481, reduced_transcript_delivered_bytes=69, over_budget=false
- aspect: permission_prompt_analysis — prompts unmeasured because the transcript arrived truncated
