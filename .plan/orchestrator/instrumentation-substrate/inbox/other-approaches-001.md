envelope_version=1
sender_type=orchestrator
sender_id=other-approaches
epic=instrumentation-substrate
kind=finding
created=2026-09-23T10:18:26Z

# Restraint-ladder wording candidate from the external token-tool evaluation

Source: `doc/other_approaches/ponytail.adoc`. The tool itself is rejected (duplicates the existing
three restraint layers: `simplicity` posture, Principle 7 "Implement the Minimum", and
`finalize-step-simplify`). Routed here because this epic owns measuring the effect of instruction
wording; this is a wording candidate, not a token lever. Ideas only — no upstream prose is imported.

## Candidate changes

1. **Ordered restraint ladder** for Principle 7 and `finalize-step-simplify`'s review criteria:
   does it need to exist → is it already in the codebase → standard library → native platform
   feature → already-installed dependency → can it be one line → only then write the minimum.
   Sharper than the current goal statement because it fixes the ORDER in which an existing answer is
   searched for before writing one.
2. **Explicit never-simplify list**: trust-boundary input validation, security, data-loss error
   handling, anything the operator asked to keep, and tests that pin a behaviour. Gives the simplify
   pass a fail-closed boundary. Relevant history: a re-fired simplify pass deleted a just-added
   regression test (process-compliance epic), and three wrong simplify deletions were reverted
   in-run (test-quality epic).
3. **In-code marker for deliberate corner-cuts**, so an intentional shortcut is distinguishable from
   an accidental one for later reviewers and simplify passes.

## Evidence caveat

The upstream claims ("16% fewer tokens", "293 → 47 lines", agentic "−54% LOC") never measured
correctness; the agentic benchmark was Haiku-only and never executed the generated code. None of
these figures may be cited as evidence. Any adoption should go through this epic's own pressure
harness with a three-valued verdict, and on more than one runtime — a Claude-only calibration is out
of bounds for the multi-model fleet. This is not a request for a de-escalation sweep.
