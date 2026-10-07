envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:12:31Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# extract-chat-signal reports success and no_signal=false after discarding 99.88% of the transcript

`extract-chat-signal run` on this plan's session returned:

```toon
status: success
raw_turn_count: 804
reduced_turn_count: 1
dropped_turn_count: 803
reduced_bytes: 278
no_signal: false
over_budget: false
```

The single surviving turn is the slash-command invocation itself. Per the SKILL's
two-tier contract, `no_signal == false AND over_budget == false` selects **Tier 1
— full analysis**, so the chat-history aspect and the permission-prompt aspect
both proceed as if they had a transcript. They analysed 278 bytes of an 804-turn
session and reported `status: success`.

## The reduction dropped real signal, not noise

Two operator interactions are independently attested in `decision.log`:

- `12:37:57` — "Operator answers applied - recovery_shape=--as-name flag
  confirmed, as_name_constraint=sender-prefix required"
- `12:48:09` — "User review: operator chose to fold the 2 pending q-gate findings
  into the outline before task planning"

Neither survived into the reduced transcript. The chat-history aspect would have
reported "no operator pivots" on a plan that had two.

The permission-prompt aspect is worse off: its whole evidence channel is the
transcript, so an empty `prompts[]` list is indistinguishable between "no prompts
occurred" and "the aspect could not see". Its `severity: warning /
confidence: high` floor exists precisely because prompts are objective state —
but that floor is meaningless when the observation channel is empty.

## Root cause

The tier decision is keyed on the `no_signal` boolean alone. There is no floor on
**retained** signal — no minimum `reduced_turn_count`, no minimum
`reduced_bytes`, no minimum retention ratio. A reduction that keeps 1 of 804
turns satisfies `no_signal: false` just as well as one that keeps 400.

## Corrective action

Add a retention floor to the Tier decision: when
`reduced_turn_count / raw_turn_count` falls below a threshold (or
`reduced_bytes` falls below a byte floor), the extractor must return a
degradation signal — a third tier, or `no_signal: true` — so downstream consumers
emit a `status: skipped` fragment with a `transcript_reduced_below_floor`
skip-reason instead of a confident empty result. Consumers must be able to tell
"looked and found nothing" from "could not look".

## Evidence

- aspect: chat_history_analysis — `reduced_turn_count: 1` of `raw_turn_count: 804`
- aspect: permission_prompt_analysis — `prompts[0]` emitted with
  `coverage_pct: 0.12` and an explicit non-evidence warning
- decision.log `12:37:57` and `12:48:09` — two operator rounds absent from the
  reduced transcript
