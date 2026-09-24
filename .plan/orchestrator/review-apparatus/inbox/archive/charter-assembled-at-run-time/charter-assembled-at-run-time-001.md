envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:11:55Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high

# Keep extract-chat-signal's reduced transcript inside its block scalar

## Context

In the plan-retrospective run for `charter-assembled-at-run-time` (session `d69e8d99-cb6e-43cc-9ae2-f14f288d1b76`), the `extract-chat-signal run` pre-pass returned `status: success` with `reduced_bytes: 193432`. The same call reported `reduced_transcript_delivered_bytes: 69`. The emitted `reduced_transcript: |` header carried only its first line indented. Every later payload line reached column 0 of the TOON document, outside the block scalar. The consumer therefore received a 69-byte payload. It derived `over_budget: false` from that payload and selected Tier 1 over an effectively empty transcript. It had 39 operator turns and 11 gate decisions it could not read.

## Root cause

The reduction is being serialized as a quoted multi-line string (the payload begins with a `"`) rather than as a `BlockScalar`-marked value, or the block-scalar indentation is applied to the first line only. That is the exact column-0 corruption `references/chat-history-analysis.md` § "Multi-line serialization" prohibits for producers.

## Proposed action

In `extract-chat-signal.py`, mark `reduced_transcript` as `BlockScalar` before `serialize_toon`, so every body line is indented two spaces. Add a round-trip test: a transcript containing a flush-left `status: blocked` line must parse back byte-identical, with `reduced_transcript_delivered_bytes == reduced_bytes`. When the two figures diverge, the pre-pass should fail loudly (or force Tier 2 with a distinct reason) rather than return `success`.

## Evidence

- aspect: chat_history_analysis: `reduced_bytes: 193432` vs `reduced_transcript_delivered_bytes: 69`, `over_budget: false`
- aspect: permission_prompt_analysis: prompt surface effectively unread; a zero here is not a trustworthy negative
