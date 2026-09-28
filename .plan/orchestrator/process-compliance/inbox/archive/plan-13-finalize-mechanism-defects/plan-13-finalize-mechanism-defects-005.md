envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=candidate-lesson
created=2026-09-28T16:10:48Z

# Route extract-chat-signal to Tier 2 when delivered bytes diverge from reduced

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_aspects: chat_history_analysis, permission_prompt_analysis

## Context

In the plan-13-finalize-mechanism-defects retrospective, `extract-chat-signal run` returned
`reduced_bytes: 258235` but `reduced_transcript_delivered_bytes: 69`. The emitted
`reduced_transcript: |` block scalar carried its first line indented and every continuation
line flush-left at column 0 (`<command-name>…`, `operator-decision: …`, `user: …`), so a
TOON parser truncates the value after one line. `no_signal: false` and `over_budget: false`
still selected Tier 1, so the chat-history and permission-prompt aspects ran on a
69-byte input while the flags reported a healthy 252 KiB reduction.

## Root cause

The multi-line serialization rule in `references/chat-history-analysis.md` (§ Multi-line
serialization) is not honoured on this path: the reduced text reaches the output without
`BlockScalar` indentation of every body line. The tier decision reads `over_budget` only, and
nothing treats a delivered/produced gap as a failed delivery.

## Proposed action

1. Emit `reduced_transcript` through `BlockScalar` so every body line is indented and
   round-trips verbatim (check whether the runtime `chat extract-signal` op or the
   `extract-chat-signal.py` pre-pass is the writer that drops the indentation).
2. When `reduced_transcript_delivered_bytes` differs materially from `reduced_bytes`, return a
   non-Tier-1 outcome (an explicit `transcript_truncated` error or Tier 2 skip) instead of
   letting `over_budget: false` select full analysis.
3. Add a regression test with a multi-line transcript containing `key: value`-shaped lines.

## Evidence

- aspect: chat_history_analysis — `reduced_bytes=258235`, `reduced_transcript_delivered_bytes=69`, `over_budget=false`, 64 operator turns / 12 gate decisions counted but not delivered
- aspect: permission_prompt_analysis — zero prompts is only a floor because the transcript input was truncated
