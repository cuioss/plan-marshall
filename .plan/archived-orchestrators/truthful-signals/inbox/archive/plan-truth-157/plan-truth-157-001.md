envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:50:34Z

# Emit reduced_transcript as one quoted scalar in extract-chat-signal output

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: plan-truth-157
source_aspects: chat_history_analysis, permission_prompt_analysis

## Context

The chat-history aspect's signal-extraction pre-pass (`extract-chat-signal run --session-id`) returned
`status: success` with `no_signal: false` and `over_budget: false`, selecting Tier 1. Its output carries
`reduced_transcript` as a MULTI-LINE value: the field opens a quoted scalar on one line and is followed by
three further physical lines at column 0, two of which (`operator-decision:` and `user:`) carry a colon at
column 0.

`chat-history-analysis.md` § LLM Interpretation Rules already states the consequence for exactly this
shape: `parse_toon` re-reads a flush-at-column-0 continuation line containing a colon as a phantom sibling
top-level key. A TOON-parsing consumer of this pre-pass output therefore recovers only the first line as
the value of `reduced_transcript`, and additionally gains up to three phantom top-level keys that were
never fields.

Beside the field, the counters describe 22 operator-signal entries (`operator_turn_count: 19` plus
`gate_decision_count: 3`) and `reduced_bytes: 27067`. Three transcript entries were legible from the
serialized field.

## Root cause

The runtime's reduction is interpolated into the pre-pass's TOON output without the newline escaping the
skill's own fragment rule requires. The rule is documented for *fragment bodies* the skill authors; the
pre-pass's own stdout was never held to it, even though it is consumed the same way.

## Proposed action

1. Escape newlines into the quoted scalar when serializing `reduced_transcript`, the same discipline
   `chat-history-analysis.md` imposes on fragment bodies.
2. Add a round-trip control asserting that `reduced_transcript` survives `serialize_toon` then `parse_toon`
   with its entry count intact, and that the parsed key set contains no key the producer did not emit.
   A matched negative arm over a single-line value proves the control is not vacuous.

## Evidence

- aspect: chat_history_analysis — "the reduced_transcript the pre-pass returned is a MULTI-LINE value ... a
  TOON-parsing consumer of this pre-pass output recovers only the first line as the field value"
- aspect: permission_prompt_analysis — the aspect's zero-prompt result had to be scoped to 3 of 22
  operator-signal entries because the remainder were not legible in the input it received
- Observed first-party by reading the captured pre-pass output for session
  3622d909-bcac-4c65-b172-f1864a5e4e23 (lines 7-10 of the captured file)

## Caveat recorded with the finding

A possible second symptom — that only 3 of 22 entries reached the consumer at all — is NOT independently
verified. It could be the truncation above, or an artifact of how the reading envelope renders very long
lines. The two causes were not distinguishable from what was read, so the entry-count gap is recorded as an
open question rather than asserted. The multi-line shape itself is directly observable and is the claim.
