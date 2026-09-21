envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:02:31Z

component=plan-marshall:phase-1-init
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# A detector that reports non-ambiguity must have measured what it is confident about

## Context

At init, `domain-detect` returned the set `{documentation, plan-marshall-plugin-dev}`
and labelled it **non-ambiguous**. `python` was surfaced separately, as an
"undetected additional candidate".

The plan it was classifying edits six Python scripts — `audit.py`, `analyze-logs.py`,
`manage-change-ledger.py`, `check-routing-decisions.py`, `file_ops.py`,
`manage-metrics.py` — and seven pytest suites, with red-first test authoring
mandatory in four of its nine deliverables. Sixteen of the 28 files in the merged
footprint are Python tests.

`python` entered the plan only because the operator overrode the recommendation at
the gate.

## Root cause

The non-ambiguity label reports the *shape of the detector's own result* (one
candidate set, no tie) rather than the *coverage of its evidence*. A detector that
looked at the wrong signal will report a clean, tie-free, confidently non-ambiguous
answer — which is exactly what happened.

"Non-ambiguous" is functionally an instruction to the reader that review is
unnecessary. Emitting it without having measured coverage is the epic's own theme
applied to routing rather than to metrics.

## Proposed action

- Gate the `non_ambiguous` label on evidence coverage, not on result shape: if a
  domain appears in the plan's declared or predicted footprint and is not in the
  returned set, the result is ambiguous by construction, regardless of tie-breaking.
- When a domain is surfaced as an "undetected additional candidate" **and** the
  footprint supports it, promote it rather than offering it — or at minimum drop the
  non-ambiguity claim.

## Counterfactual cost

Had the operator accepted the recommendation (it was presented as the resolved
answer), the plan would have carried the wrong skill set through all five remaining
phases, on a plan whose entire subject was Python reader behaviour and whose
verification contract was red-first pytest authoring.

## Evidence

- aspect chat_history_analysis: the verbatim gate question and the
  "Add python (Recommended)" disposition
- `manage-solution-outline list-deliverables`: six .py write-intent paths, seven
  pytest suites
- merged footprint: 16 of 28 files are Python tests
