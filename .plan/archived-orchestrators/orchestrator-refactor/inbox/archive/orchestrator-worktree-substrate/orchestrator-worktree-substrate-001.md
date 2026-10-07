envelope_version=1
sender_type=plan
sender_id=orchestrator-worktree-substrate
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-28T19:16:47Z

component=plan-marshall:plan-retrospective
category=bug

# Deliver the full reduced transcript from extract-chat-signal as an indented block

## Context

In the orchestrator-worktree-substrate retrospective, `extract-chat-signal run --session-id 3f7ea31c-...` reported `reduced_bytes: 236070` (56 operator turns, 9 gate decisions) but `reduced_transcript_delivered_bytes: 69`. In the emitted payload only the first line of `reduced_transcript: |` was indented; every continuation line reached column 0. Tier 1 was selected (`no_signal: false`, `over_budget: false`), so the chat-history aspect ran on a near-empty payload.

## Root cause

The block-scalar body is not indented past its first line on this path, so `parse_toon` reads the continuation lines as sibling top-level keys and truncates the value. That is exactly the multi-line serialization rule `references/chat-history-analysis.md` states. Because `over_budget` is derived from the delivered bytes, a truncated delivery also passes the budget gate.

## Proposed action

Emit `reduced_transcript` as a `BlockScalar` with every line indented, and add a round-trip test on a multi-line reduction. Add a guard that fails, or downgrades to Tier 2 with a named reason, when `reduced_transcript_delivered_bytes` is much smaller than `reduced_bytes`. At present a large gap between the two figures silently selects Tier 1.

## Evidence

- aspect: chat_history_analysis - delivered 69 of 236070 reduced bytes, Tier 1 selected
- aspect: permission_prompt_analysis - prompt population limited by the same truncated delivery
