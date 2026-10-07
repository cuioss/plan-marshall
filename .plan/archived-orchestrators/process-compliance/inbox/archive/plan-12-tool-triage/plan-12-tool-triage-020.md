envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:58Z

# A `loop_back_target: 6-finalize` round has no documented fix-applier on the unattended path

## Observed

`pre-submission-self-review` round 1 of plan-12-tool-triage returned 8 findings (5 `contract_drift`, 3
`regex_overfit`). Per its Step 4 Branch B it recorded `--outcome loop_back --loop-back-target 6-finalize` —
"the inline-fixable tier: the findings are addressed on this branch and the finalize step loop is
re-entered, with no phase-5-execute re-dispatch".

With `loop_back_without_asking: true`, `phase-6-finalize/SKILL.md` item 7b's `6-finalize` granularity branch
says only: "BREAK out of the current FOR iteration and RE-ENTER the FOR loop from the start … The resumable
re-entry check sees the loop_back-marked step and re-fires it directly." No step, dispatch, or workflow in that
branch APPLIES the fixes. The only statement of who fixes is the self-review doc's closing line: "The operator
must address every finding … re-run the step, and only then advance to push" — which contradicts the unattended
auto-continue the knob selects.

Followed literally, the re-fired self-review runs a delta round against an unchanged HEAD (empty delta → clean
filter result → mandatory full re-sweep → the same 8 findings → loop_back again) until the `max_iterations`
ceiling refuses admission. The loop cannot converge by construction, and every iteration costs a full author +
verifier dispatch pair.

The orchestrator asked the operator, who chose to dispatch one execution-context fix run over the pending
6-finalize findings before re-entering — an undocumented step.

## Suggested fix

Give the `6-finalize` inline tier a defined fixer: e.g. route a findings-bearing `loop_back` with target
`6-finalize` through `verification-feedback` (`producer=self-review`) to produce inline edits, or dispatch a
documented "apply inline findings" workflow before the re-entry. Until then, `loop_back_without_asking: true`
should not be honoured for a target that no step can make progress on.
