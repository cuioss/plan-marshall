envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:09:47Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=medium
source_aspects=chat-history-analysis

# Chat-history aspect is blind to AskUserQuestion-mediated operator input

## Context

The chat-history aspect reads the session transcript to characterise operator involvement. On this plan the pre-pass reduced 399 turns to 3 (352 bytes): one slash command and the word "continue" twice. Taken at face value, the operator did nothing but launch and wave through.

The record says otherwise. Four substantive operator interventions shaped this plan, and all four are in `decision.log`, not the transcript:

- three outline answers settling D1 (`propagate-None`), D2 (`correct-docs-only`) and the write boundary;
- a direction to resolve all three pending q-gate findings and re-dispatch outline;
- a decision to SUPERSEDE settled decision D1 and narrow `_interpreter_ok` — reopening a boundary the outline had closed;
- a decision to merge on green over an explicitly accepted review-coverage gap.

The last two are exactly the operator dispositions the `finalize-step-preference-emitter` and the archived-plan audit's preference-pattern detector are meant to learn from.

## Root cause

Operator input migrated to structured `AskUserQuestion` prompts, whose content lands in `decision.log`. The aspect's input contract still assumes free-text chat is where the operator speaks.

## Proposed action

Add `decision.log` operator-disposition lines as a second input to the aspect, so "operator involvement" is measured over both channels. Alternatively, have the aspect declare its channel explicitly — reporting "free-text channel only; N structured dispositions not covered" — so a thin transcript is not mistaken for a disengaged operator.

Secondary observation for the same component: `extract-chat-signal` returned `no_signal: false` on a payload whose entire user content is one slash command and two bare `continue` tokens. The predicate passes on a payload with no analysable narrative, which makes `no_signal` a weaker gate than its name suggests.

## Evidence

- `extract-chat-signal run` — `raw_turn_count: 399`, `reduced_turn_count: 3`, `reduced_bytes: 352`, `no_signal: false`
- `reduced_transcript` content — `/plan-marshall:plan-marshall task=...`, `continue`, `continue`
- decision.log `3798d8`, `4e1655`, `c934c3`, `309777` — the four operator interventions, none present in the transcript reduction
