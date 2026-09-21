envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:00Z

# extract-chat-signal truncates reduced_transcript while reporting its full size

component: plan-marshall:plan-retrospective
category: bug
confidence: high

## Context

The chat-history aspect (aspect 14) is gated by a two-tier decision: when `no_signal == false` AND `over_budget == false`, the orchestrator is instructed to feed `reduced_transcript` to the LLM analysis prompt. On this plan the pre-pass returned exactly that Tier-1 state — `no_signal: false`, `over_budget: false`, `reduced_bytes: 536022`, `kept_raw_count: 96`, `operator_turn_count: 95` — and the `reduced_transcript` field it delivered carried roughly 1.5 KB spanning 7 turns.

A differential probe settles which side of the hop loses the payload. Invoking the platform-runtime operation directly (`platform_runtime chat extract-signal --session-id ...`) emits the full multi-line reduction. Invoking the documented consumer (`plan-retrospective:extract-chat-signal run --session-id ...`) emits the truncated one. The runtime is correct; the consumer is lossy.

## Root cause

`extract-chat-signal.py` re-parses the runtime operation's TOON output with `parse_toon(result.stdout)` (line 92) and then forwards `record.get('reduced_transcript', '')` verbatim (line 165). `parse_toon` does not round-trip a multi-line string value, so the field survives the hop only as its leading fragment. Every sibling field is a single-line scalar and survives intact — including `reduced_bytes`, which is the *runtime's* measurement of what the runtime produced, not a measurement of what the consumer delivered.

The two numbers therefore come from opposite sides of the lossy hop and can never disagree visibly. Worse, `over_budget` is derived by the consumer from that same unreachable `reduced_bytes` (line 145), so the gate that decides whether the payload is small enough to analyse is computed over a size the payload does not have. Tier 1 opens onto a payload the consumer structurally cannot supply.

## Proposed action

Stop routing the transcript through a TOON re-parse. Either have the runtime operation write the reduction to a file and return its path (the consumer then forwards the path, and no multi-line value crosses a TOON boundary), or give `parse_toon`/`serialize_toon` a tested multi-line round-trip and pin it with a fixture whose value contains embedded newlines.

Independently of which fix is taken, add a conservation assertion in the consumer: `len(reduced_transcript.encode()) == reduced_bytes`, or publish both figures side by side as `reduced_bytes_reported` and `reduced_bytes_delivered` so a consumer can see the shortfall. A single reported size that measures the wrong side of the hop is the defect; publishing both makes it self-evident.

## Evidence

- aspect: chat_history_analysis — `reduced_bytes_reported: 536022` beside `reduced_transcript_bytes_delivered: 1500`, `turns_actually_available_for_analysis: 7` of `kept_raw_count: 96` (7.3% coverage)
- aspect: permission_prompt_analysis — the aspect's only population is this transcript, so its `prompts: 0` is an under-covered zero rather than a checked negative
- differential probe: runtime op output is the full multi-line reduction; consumer output is ~1.5 KB
- source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py` lines 92, 145, 162, 165
