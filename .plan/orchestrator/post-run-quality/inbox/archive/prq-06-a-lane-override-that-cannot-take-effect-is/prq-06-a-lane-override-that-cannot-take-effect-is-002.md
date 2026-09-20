envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:21Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=chat_history_analysis,permission_prompt_analysis

# extract-chat-signal Tier-1 payload is truncated to its first line

## Context

The chat-history aspect's two-tier gate selected Tier 1 for this plan. The pre-pass returned:

```
status: success
reduced_bytes: 311791
reduced_turn_count: 52
operator_turn_count: 52
gate_decision_count: 4
no_signal: false
over_budget: false
```

Every flag says "full analysis, the transcript fits the budget". The stdout that carries the transcript is roughly 4.4 KB and contains **two** readable operator turns out of the 52 counted — about 4% of the reported signal. `reduced_transcript` is emitted as a multi-line TOON scalar and only its first quoted line round-trips, so the consumer receives a fraction of the payload with nothing in the return saying the payload was cut.

## Root cause

`serialize_toon` never emits block scalars, and the reduction is inherently multi-line. The producer writes the whole reduction as one quoted scalar whose continuation lines sit flush at column 0. The consequence is twofold:

1. **Truncation** — the value does not survive the round trip, so `reduced_bytes` describes a payload the caller never receives.
2. **Structural corruption** — `chat-history-analysis.md` § LLM Interpretation Rules (final bullet) warns aspect authors that "any continuation line that sits flush at column 0 and contains a colon is re-parsed by `parse_toon` as a phantom sibling top-level key, leaking a spurious aspect into the bundle." Line 9 of the emitted output is literally `operator-decision: "Your questions have been answered: ..."` flush at column 0. The producer commits the exact defect its own consumer document forbids.

## Proposed action

Stop passing the reduction through a TOON scalar. `extract-chat-signal` should write the reduced transcript to a file and return its **path** (mirroring how every other large artifact in this pipeline is handed over — `--fragment-file`, `--payload-file`, `--diff-file`), leaving the TOON return to carry the counts and flags only.

As a guard, make the Tier decision verifiable at the consumer: have the pre-pass publish `reduced_transcript_delivered_bytes` alongside `reduced_bytes`, so a consumer can detect the mismatch instead of silently analysing 4% of the corpus and reporting `status: success`.

## Evidence

- aspect: chat_history_analysis — `reduced_bytes: 311791` / `reduced_turn_count: 52` against 2 readable operator turns
- the emitted scalar's continuation lines 8-12, with `operator-decision:` at column 0
- aspect: permission_prompt_analysis — forced to report an UNMEASURED zero rather than a clean one, because 50 of 52 operator turns and 3 of 4 gate-decision bodies were never delivered
- `references/chat-history-analysis.md` § LLM Interpretation Rules, final bullet — the rule the producer violates
