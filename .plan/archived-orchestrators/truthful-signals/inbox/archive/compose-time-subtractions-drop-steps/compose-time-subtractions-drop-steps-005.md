envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:36:06Z

## Proposed lesson metadata

- `component`: `plan-marshall:manage-execution-manifest`
- `category`: `improvement`
- `title`: D3 gap — two phase-5 subtraction sites still report only to the decision log, not the compose result

## Observation (residual owed to the epic)

`decision-rules.md` now states normatively that **every subtraction is
reported**. That statement is not yet fully true. Two phase-5 sites subtract
without emitting a compose-result record:

1. `canonical_verify_inactive`
2. the verify-step **resolvability filter**

Both emit only a decision-log line. A decision-log line is a *narrative* signal
readable by a human tailing the log; the compose-result record is the
*structured* signal every downstream consumer (retrospective, manifest audit,
finalize-flow conformance) actually reads. A consumer asking the compose result
"what was dropped?" gets an answer that omits these two.

## Why this is filed rather than fixed

The gap is **named in `decision-rules.md`** rather than silently overclaimed —
the doc says the rule is normative and calls out these two sites as not yet
conformant. That is the honest disposition and it is deliberately not a false
green. But it is a real D3 gap and it is owed.

Note the shape: this is exactly the epic's theme. The normative sentence "every
subtraction is reported" is a confident signal; the caveat lives two paragraphs
below it. A reader who quotes the rule without the caveat will believe the class
is closed.

## Owed work

Emit a compose-result drop record from both sites, matching the record shape the
other 11 predicates now use, and then delete the caveat from `decision-rules.md`
— the caveat's deletion is the acceptance criterion.
