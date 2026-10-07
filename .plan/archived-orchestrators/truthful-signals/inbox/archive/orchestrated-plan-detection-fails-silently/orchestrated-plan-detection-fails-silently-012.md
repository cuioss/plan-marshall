envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:17:40Z

component=plan-marshall:plan-retrospective
category=improvement
bundle=plan-marshall

# extract-chat-signal reports no_signal=false after retaining 2 of 655 turns, so the chat aspect passes green on 0.3% of the transcript

## What happened

`extract-chat-signal run` on PLAN-114's session returned:

```
status: success
raw_turn_count: 655
reduced_turn_count: 2
dropped_turn_count: 653
reduced_bytes: 682
no_signal: false
over_budget: false
```

`no_signal: false` and `over_budget: false` together are the **Tier 1** verdict — "usable signal, proceed with LLM analysis". The two retained turns are the slash-command invocation and one background-task completion notification. Neither is an operator interaction.

The plan definitely had operator interactions. From `decision.log` alone:

- 13:24:12 — execution-profile posture overridden by the operator to `auto` against the router's `minimal` projection
- 13:24:42 — the D1 id-grammar gate **settled by operator**, three accepted forms
- 13:24:44 — operator added the `python` and `documentation` domains
- 13:19:03 — `lane_selection=ask`, so at least one AskUserQuestion round-trip fired

All four were dropped by the reducer. They are recoverable in this retrospective only because `decision.log` independently recorded them — which is luck, not design.

## Root cause

`no_signal` answers **"did the reducer find any keeper turns at all?"** The Tier-1/Tier-2 branch consumes it as though it answered **"is the retained slice sufficient for analysis?"** Those are different questions, and at 0.3% retention they give opposite answers.

There is no floor. One retained turn of 655 is `no_signal: false`.

## Corrective rule

1. **Add a retention floor to the tier decision.** Below a threshold (retention ratio, absolute retained-turn count, or retained bytes) the pre-pass must emit the Tier-2 path with a distinct skip-reason token — something like `signal_below_analysable_volume` — rather than `no_signal: false`. The existing token contract already distinguishes `transcript_too_large` from `transcript_unavailable`; this is the third genuine state and it currently has no token.
2. **Emit `retention_ratio` as a first-class field** so a consumer that does not want to gate on it can still report it. This aspect's fragment should carry it into the report unconditionally.
3. **Audit the keeper heuristic against operator-decision turns.** A reducer that drops an `AskUserQuestion` exchange while keeping a background-task notification has its priorities inverted for this aspect's purpose — the whole point of chat-history analysis is operator interaction quality.

## Why it matters for truthful signals

The aspect reported `status: success` and produced a fragment. Nothing in the pipeline says "the qualitative half of operator-interaction coverage was not actually assessed." A reader of the retrospective sees a Chat History Analysis section and reasonably concludes the transcript was analysed.

**A reducer's "I found signal" is not the same claim as "I retained enough signal to answer the question."** Collapsing the two lets an aspect pass green on a sample too small to support any conclusion — the volume-read-as-coverage archetype, inverted: here a near-zero volume is read as adequate coverage.

## Evidence

- `extract-chat-signal` output quoted above, run against `~/.claude/projects/-Users-oliver-git-plan-marshall/fe441faa-3da0-4e5d-ad96-38aa5509152a.jsonl`
- `decision.log` 13:19:03, 13:24:12, 13:24:42, 13:24:44 — the four dropped operator interactions
