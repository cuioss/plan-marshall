envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:07:33Z

component=plan-marshall:manage-execution-manifest
category=bug
created=2026-07-29

# The scope gate silently reversed an explicit operator override — and logged an immunity carve-out for a different step in the same run

## The sequence

```
[13:35:00] (phase-1-init) Execution-profile posture: auto (projected=minimal, lane_selection=ask)
           - operator overrode upward to retain pre-submission-self-review and simplify
...
[14:02:35] (manage-execution-manifest:compose) scope_gated_finalize subtraction — scope_estimate=surgical,
           dropped pre-submission-self-review from phase_6.steps
```

The operator was asked, answered, and their answer named `pre-submission-self-review` specifically. Twenty-seven minutes later an implicit scope gate removed exactly that step. The operator was never told.

## What makes this sharp rather than merely unfortunate

The **same compose run, the same second**, recorded this:

```
[14:02:35] scope_gated_finalize immunity — kept plan-marshall:plan-retrospective despite scope_estimate=surgical:
           the step declares an explicit non-auto lane override, which the implicit scope gate must not silently override
```

So the mechanism for "an explicit override must not be silently overridden by an implicit gate" **already exists and already fired in this run** — it is keyed on a step's declared `lane` parameter, and it is not keyed on operator intent. A step's own config is protected from the scope gate; a human's recorded answer is not.

## Solution

Persist the operator's profile-override answer as a first-class immunity input, in the same shape the step-level `lane` override already uses, so `scope_gated_finalize` skips any step the operator named when raising the posture. Failing that, the subtraction MUST emit a warning naming the operator decision it is reversing — a silent subtraction of an operator-requested verification step is not an acceptable outcome.

## Impact

An operator who deliberately buys extra verification gets billed for the decision (the upward posture) and does not receive the verification. The decision log makes it recoverable only to someone who reads two entries 27 minutes apart and notices they contradict; every summary surface shows a clean manifest.
