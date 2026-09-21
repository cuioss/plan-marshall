envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:17:32Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=plan-130-sweep-the-prose-the-widened-rules

# Validate required self-review prompt fields before dispatch, not in the leaf

## Context

During 6-finalize the `pre-submission-self-review` step was dispatched without its required `candidates` prompt field. The dispatched leaf refused the work and returned nothing rather than producing a verdict over an input it had not been given. The step was recorded `outcome=error` at 2026-09-06T21:10:08Z, having consumed 144,380 tokens across 10 tool uses, and the whole step then had to be re-dispatched, completing at 21:12:34Z.

The leaf's behaviour was correct and is the reason this shows up as a cost rather than as a false clean verdict: a leaf that had guessed a candidate set would have returned "no check matched" over a population nobody chose, and the step would have passed green having reviewed nothing.

## Root cause

The required-field check lives only inside the dispatched envelope. The dispatcher composes the prompt body and fires it with no validation, so a missing required field is discovered one full envelope late — after the model, the context load and the skill loads have all been paid for.

## Proposed action

Validate the self-review dispatch's required prompt fields in `phase-6-finalize` before the `Task:` dispatch is issued. The check is a presence test over a small declared field list and costs nothing next to a 144K-token round trip. More generally: for any finalize step whose leaf declares required prompt-body fields, the dispatcher should assert them at compose time.

## Evidence

- aspect: logging_gap_analysis — `6-finalize` carries `error_total_tokens: 144380`, `retryable_total_tokens: 0`; the whole figure is this one dispatch, and none of it is infrastructure a re-run recovers.
- aspect: execution_context_dispatch_audit — `dispatch_coverage` classifies `pre-submission-self-review` as `dispatched`; the boundary row at 2026-09-06T21:10:03Z carries `termination_cause: error`.
- decision log 2026-09-06T21:10:08Z — `Recorded pre-submission-self-review phase=6-finalize outcome=error — total_tokens=144380, tool_uses=10, duration_ms=110295`.
