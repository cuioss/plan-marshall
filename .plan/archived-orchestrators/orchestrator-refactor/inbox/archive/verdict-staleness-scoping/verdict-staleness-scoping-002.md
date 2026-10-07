envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:21Z

# Gate chat-history Tier 1 on the delivered-vs-reduced byte gap

## Metadata

- component: `plan-marshall:plan-retrospective`
- category: improvement
- confidence: high
- observed_in_plan: verdict-staleness-scoping

## Context

`chat-history-analysis.md` publishes `reduced_bytes` and `reduced_transcript_delivered_bytes`
side by side and states explicitly that "the gap between them is itself the signal when they
do not [agree]". On this plan the gap was 3957x — 273005 produced, 69 delivered — and the
aspect still selected Tier 1 and would have reported `status: success` over 0.025% of the
session. Nothing in the pipeline compares the two figures.

## Root cause

The instrument exists and publishes the discrepancy, but no consumer routes on it.
`extract-chat-signal.cmd_run` computes `over_budget = delivered_bytes > read_budget` — a
one-sided test against the POST-truncation figure. Truncation makes `delivered_bytes` small,
so `over_budget` is driven to `false` by the very failure it would need to detect: the Tier-2
guard is structurally incapable of firing on this path, however large the session was.

## Proposed action

Add a delivery-integrity check beside the budget check: when
`reduced_transcript_delivered_bytes` is materially below `reduced_bytes`, the aspect must not
enter Tier 1 silently. Either extend the closed skip-reason token set with a third token for
delivery loss (the contract states a third token requires updating the contract and every
aggregation consumer, so this is a deliberate change, not a drive-by), or keep Tier 1 and
require the fragment to publish a `delivery_coverage` block with an `error` finding. The
narrower half — comparing the two figures at all — should land regardless.

## Evidence

- aspect: chat_history_analysis — Tier 1 entered on the contract's own condition while 99.975% of the reduced payload was missing
- source: `chat-history-analysis.md` § Two-Tier Degradation Path names the gap as the signal
- source: `extract-chat-signal.py:187` — `over_budget = delivered_bytes > read_budget`, with no comparison against `reduced_bytes`
