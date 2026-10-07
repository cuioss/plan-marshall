envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:21Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high

# Emit reduced_transcript so it survives its own TOON envelope

## Context

`extract-chat-signal run` reported `reduced_bytes: 4725` across `operator_turn_count: 8` and `gate_decision_count: 6`. Roughly 700 bytes of that reduction are actually recoverable from the emitted TOON.

The value is emitted as a quoted scalar whose continuation lines sit flush at column 0 and contain colons — for example a line beginning `operator-decision: "Your questions have been answered..."`. That is precisely the shape `references/chat-history-analysis.md` line 97 warns about:

> any continuation line that sits flush at column 0 and contains a colon is re-parsed by `parse_toon` as a phantom sibling top-level key, leaking a spurious aspect into the bundle

The reference states that rule as an obligation on fragment AUTHORS. The producer script emits exactly the prohibited shape itself.

## Root cause

The warning was written as authoring guidance for hand-written fragments, and was not applied to the script that produces the multi-line value those fragments consume. The byte count is computed before serialization, so the envelope advertises the full reduction while delivering a fraction of it.

## Proposed action

Emit `reduced_transcript` in a form that round-trips - escape the embedded newlines into a single-line quoted scalar, or carry the reduction as a side file referenced by path. Either way, make the delivered size checkable against `reduced_bytes` so a lossy envelope is detectable rather than silent.

## Evidence

- fragment produced by `extract-chat-signal run --session-id a157020a-5983-4fba-9b08-133caefea85e`: `reduced_bytes: 4725`, `reduced_turn_count: 8`, `operator_turn_count: 8`, `gate_decision_count: 6`; recoverable text approximately 700 bytes.
- marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md line 97 - the rule the producer violates.
- Downstream effect: the permission-prompt aspect could not reach a verdict on this run and returned `not_evaluated`, because roughly 85% of the operator-authored signal it analyses was unreadable.
