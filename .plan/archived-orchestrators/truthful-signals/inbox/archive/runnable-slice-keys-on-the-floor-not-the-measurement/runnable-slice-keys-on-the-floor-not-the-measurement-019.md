envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:13:12Z

component=marshall-orchestrator
category=insight
created=2026-07-29

# Four signals refused to lie this run — the counterexample set

An epic themed on confident-signals-hiding-caveats needs its positive control.
Four components in this run had the opportunity to emit a convenient falsehood
and declined, each in a different way. They are the shapes to copy.

**1. safe-merge refused an immediate merge and named the remedy.** It detected
that `main` has a required platform merge queue and that an immediate merge would
close the PR unmerged (#866). It did not force, and it did not fail vaguely — it
stated the structural reason and the correct alternative. A refusal that carries
its cause is actionable; a refusal that carries only a status code is not.

**2. `collect-fragments add` rejected an unregistered aspect key loudly.** Given
`--aspect invariants` (the plausible-but-wrong name for `invariant-summary`) it
returned an error enumerating all 17 valid keys AND stating the consequence it
was preventing: "compile-report would silently drop its section". It chose a loud
rejection over a silent drop, and it explained which silent failure it existed to
prevent. Registry-backed key validation is the structural cure for the
invented-name archetype that produced 11 argparse rejections elsewhere in this
same run.

**3. Two leaves refused to exceed the leaf invariant rather than faking it.**
`phase-6-finalize` halted at manifest step 2 and returned resumable state naming
the exact step and its recorded predecessor. `pre-submission-self-review` logged
a `[DEVIATION]` WARNING ("Leaf cannot dispatch further - running LLM cognitive
checks inline iteration=2") and degraded to inline execution with the deviation
surfaced rather than swallowed. Neither pretended to dispatch.

**4. `metrics.md` published its own incompleteness.** It renders
`> Partial: unrecorded phases — 6-finalize` and marks every total `(n=4/6)` /
`(n=5/6)`, so the 1,906,522-token figure is legible as a floor rather than a
truth. A total that states its own denominator cannot be misread as complete.

## Impact

The common structure across all four: each signal carries the SCOPE of its own
validity alongside its value — the refusal carries its cause, the rejection
carries its valid set and its rationale, the halt carries its resumable state,
the total carries its denominator. That is the design rule the defect cases in
this epic all violate in one way or another, and it is cheap to apply: attach the
qualifier to the verdict, in the same field, on the same channel.
