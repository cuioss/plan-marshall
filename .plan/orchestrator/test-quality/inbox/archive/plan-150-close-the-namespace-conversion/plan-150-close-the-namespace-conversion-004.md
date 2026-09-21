envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:53:45Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=plan-150-close-the-namespace-conversion

# Validate a step's requires_prompt_fields before firing its dispatch

## Context

At 2026-09-02T20:04:38Z the finalize dispatcher fired `pre-submission-self-review` without
the `candidates` prompt-body field that step declares under `requires_prompt_fields`. The
leaf refused, correctly and for two stated reasons: it would not issue an absence claim over
a candidate set nobody had surfaced, and it would not write a failed terminal record whose
`head_at_completion` would then become a bogus `--since-ref` anchor for the next round.

The refusal was the right behaviour at every level. It still cost 130,209 tokens — the
single largest genuinely non-productive spend in the run, and the whole of `6-finalize`'s
`error_total_tokens` (`retryable_total_tokens` is 0, so this is not infrastructure noise).
The dispatcher then ran the surfacer inline and re-dispatched successfully, and round 1 of
the completed review found 4 defects the external review bots did not.

## Root cause

The dispatch site composes the prompt body by hand and nothing checks it against the
target step's declared `requires_prompt_fields` before the envelope is spent. A contract
that is enforced only at the receiving end is enforced after the cost has already been paid.

## Proposed action

Pre-flight the composed prompt body against the step's declared `requires_prompt_fields` at
the dispatch site, and refuse locally when a required field is absent. The check is a set
difference over data the dispatcher already holds, and it converts a 130K-token round trip
into a zero-cost local failure that names the missing field.

## Evidence

- work.log 2026-09-02T20:05:50Z ERROR — "Refused: required prompt-body field 'candidates' absent from dispatch; workflow forbids re-invoking the surface helper"
- work.log 2026-09-02T20:06:39Z WARNING — "Dispatcher error, not a step failure: running the surfacer inline and re-dispatching with candidates forwarded"
- aspect: log_analysis — `dispatch_boundaries.6-finalize`: one `error` row at 2026-09-02T20:06:37Z, `total_tokens: 130209`; `error_total_tokens: 130209`, `retryable_total_tokens: 0`
- status.metadata.phase_steps — `pre-submission-self-review`: `prior_firings: [failed]`, `firing_count: 2`
