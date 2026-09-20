envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:07:47Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# `extract-chat-signal` reports `no_signal: false` over a reduction that dropped every operator-decision turn

## Observed

```
$ extract-chat-signal run --transcript-path .../c276a8e2-....jsonl
raw_turn_count: 805
reduced_turn_count: 5
dropped_turn_count: 800
no_signal: false
over_budget: false
```

`no_signal: false` routes the caller to **Tier 1** — "feed `reduced_transcript` to the LLM analysis prompt". Here is what the retained 5 turns actually contain:

1. the `/plan-marshall` launch command
2. one assistant line about a Tier-1 inline decision
3. a merge-lock admission task-notification
4. a monitor stream-ended task-notification
5. a monitor timed-out task-notification

Three of five retained turns are **machine task-notifications**. Meanwhile this plan recorded two substantive operator interactions in its decision log — the D1 gate disposition (`3c7ad9`, a multi-clause instruction about what the outline must establish) and the upward execution-profile override (`4b563f`) — and **neither survived the reduction**.

## The defect

The extractor's retention predicate keeps `<task-notification>` blocks (they are `user`-role envelopes) and drops the operator turns that carry actual decisions. It then reports signal-present with full confidence. The chat-history aspect exists specifically to analyse operator interaction; it was handed a corpus with none in it and told the corpus was good.

A Tier-2 `status: skipped` with `transcript_unavailable` would have been *more* truthful than the Tier-1 pass this produced — the contract has an honest degradation path and the predicate steers away from it.

## Solution

- Exclude `<task-notification>`, `<command-message>`, `<command-name>` and other harness-generated `user`-role envelopes from the signal population before computing `no_signal`.
- Compute `no_signal` from **operator-authored** turns only, and emit the operator-turn count in the output so a caller can see the basis of the verdict.
- Emit `retained_kinds` so a downstream reader can tell a 5-turn reduction full of notifications from a 5-turn reduction full of decisions.

## Impact

Any chat-history aspect finding — and any cross-plan audit of operator-interaction patterns or preference detection built on this extractor — is derived from a population that systematically keeps harness noise and discards the operator. The failure is silent and consistent, so it will look like "operators rarely intervene" rather than like a bug.
