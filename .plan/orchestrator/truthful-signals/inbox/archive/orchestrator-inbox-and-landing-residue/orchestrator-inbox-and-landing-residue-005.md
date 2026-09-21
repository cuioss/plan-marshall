envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:53:35Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=permission_prompt_analysis,chat_history_analysis

# Permission-prompt aspect returns an unfalsifiable zero in finalize-step mode

## Context

Aspect 9 (permission-prompt analysis) declares itself "conditional: only meaningful when a `--session-id` is present OR the plan's chat-history analysis surfaced one or more `permission_prompts` entries". A `--session-id` was present, so the aspect was in scope and ran.

Its documented inputs are the session transcript and the chat-history aspect fragment. But the only transcript reader available to this workflow is `extract-chat-signal`, whose reduction keeps operator text turns and `operator-decision` gate records and drops everything else. Across the two transcripts it dropped 2020 of 2031 raw turns. A permission prompt is neither an operator text turn nor an `AskUserQuestion` gate decision, so it cannot survive that reduction.

The aspect therefore emits `prompts[0]` on every finalize-step run, whether or not a prompt fired. Nothing distinguishes "no prompt fired" from "a prompt fired and the reducer discarded it".

## Root cause

The aspect's severity contract is explicit that a prompt is an **observed event**, not an inference: "there is no inference chain whose confidence could reasonably be below high". That contract is sound, and it is exactly why the empty result is a problem — the aspect has no observation channel at all in this mode, yet its output is shaped identically to an observation that found nothing.

This is the same could-not-look-reports-clean shape the `truthful-signals` epic exists to close, applied to the retrospective's own aspect table. `compile-report` did not flag it: `sections_unattributed_zero` came back empty for this run only because the fragment was written with an explicit `coverage_caveat` block. A fragment emitting a bare `prompts[0]` would have been caught; the underlying blindness would not.

## Proposed action

Pick one of two:

1. **Give the aspect an evidence channel** — add a permission-prompt retention rule to `extract-chat-signal` so prompt events survive the reduction alongside operator turns and gate decisions. The events are machine-identifiable in the raw transcript, so this is a reducer rule, not a new parser.
2. **Make the blindness structural** — have the aspect emit `status: not_evaluated` with a reason in finalize-step mode, so `compile-report`'s `ZERO_DECLARED_UNMEASURED_STATUSES` vocabulary catches it and the report says the section could not look.

Option 1 is preferable: the aspect exists because permission prompts are a recurring friction source, and permanently marking it unevaluated retires a check rather than fixing it.

## Evidence

- aspect: permission_prompt_analysis — `coverage_caveat: "This is a COULD-NOT-LOOK zero, not an evaluated-clean zero ... 2020 of 2031 raw turns were dropped"`
- `extract-chat-signal` outputs: `raw_turn_count: 1691 / reduced_turn_count: 10` and `raw_turn_count: 340 / reduced_turn_count: 1`
- `references/permission-prompt-analysis.md` § "LLM Interpretation Rules" — the severity-floor rule that makes the empty result contradictory
