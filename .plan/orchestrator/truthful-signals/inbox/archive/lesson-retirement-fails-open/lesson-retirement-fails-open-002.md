envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:02:43Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Four retrospective checks publish verdicts over populations they never established

## Context

The retrospective of plan `lesson-retirement-fails-open` — a plan whose entire
thesis is that a benign zero must not stand in for could-not-look — found that
same collapse in four independent checks of the retrospective machinery itself.

1. **`check-artifact-consistency` cannot resolve the footprint at all in
   finalize-step mode.** `affected_files_recall` and `affected_files_exact_match`
   both returned `inconclusive` because the worktree was removed by `branch-cleanup`
   and the legacy `references.modified_files` fallback key no longer exists. In the
   registered step order `plan-marshall:plan-retrospective` always runs after
   `branch-cleanup`, so two of this aspect's six checks are unmeasurable on every
   finalize-step run, not just this one. The aspect reported `inconclusive` honestly
   — which is correct behaviour and NOT the defect — but a check that can never
   measure is dead weight the report still carries.

2. **`shape_violation` returned zero from an empty population.** The check pairs
   `decision.log` `effort resolve-target` entries against `work.log` `[DISPATCH]`
   lines. This plan's `decision.log` holds 76 entries and zero `resolve-target`
   records, so Surface B is empty and the check cannot fire regardless of the
   truth. A zero emitted from an unestablished population is exactly the defect
   under audit.

3. **`dispatch_coverage_violation` pairs at step granularity and is blind to the
   re-entry gap.** The check confirms "at least one `[DISPATCH]` line carries the
   step's role". `pre-submission-self-review` (4 dispatches, 2 lines),
   `project:finalize-step-plugin-doctor` (2 dispatches, 1 line) and
   `plan-marshall:automatic-review` (2 dispatches, 1 line) all PASS while together
   accounting for 5 unlogged dispatches. It measures whether a step ever
   dispatched, not whether every dispatch was logged.

4. **`check-routing-decisions` named a removal cause it did not establish.** It
   reported `mis_prune:sonar-roundtrip` as "skipped as `no_code_delta` but the
   realized footprint touched production code". `decision.log` entry `9e1b0f`
   records the actual cause verbatim: dropped because `execution_profile=standard`
   and the step's effective tier `full` exceeds the posture cutoff. The
   `no_code_delta` predicate was never consulted. The script already parses that
   very decision line into `recorded_lane_decisions[]`.

A fifth instance sits in the same family: `script-failure-analysis` assigns
confident `anti-pattern` / `bug` categories from stderr signature alone, and three
of its six unique findings on this plan are misclassified — an argument-ORDER
error reported as `invented_flag`, a designed precondition rejection reported as an
argparse anti-pattern, and an agent notation error reported as a script-internal
bug.

## Root cause

Each check computes a verdict from whatever its input surface happened to contain,
without first asserting that the surface was populated and that the population is
the one the verdict claims to be about. The vocabulary to say "could not look"
exists in one place (`inconclusive`, used correctly by `check-artifact-consistency`)
and is absent from the other four.

## Proposed action

- Give `check-artifact-consistency` a post-merge footprint fallback: when no
  worktree is on disk, derive the footprint from the landed merge commit using the
  PR sha already in `status.metadata`, and report the provenance alongside the list.
  This retrospective recovered the 19-path footprint that way in one command.
- Make `shape_violation` report `unmeasurable` with the observed Surface B size
  whenever the resolve-target population is empty, never `0`.
- Pair `dispatch_coverage_violation` at dispatch granularity — `[DISPATCH]` lines
  against envelope completions per step — and publish the envelope-completion
  population next to the line count so the ratio is visible.
- Give `check-routing-decisions` a distinct `removal_cause` for a posture-tier drop
  versus a `prunable_when` predicate evaluation, and refuse to report a mis-prune
  for a step whose predicate never fired.
- Add `precondition_rejection` and `argument_order` categories to
  `script-failure-analysis`, keyed on the exit path rather than the usage string.

## Impact

Every retrospective in the corpus. Four of the six candidate lessons this run
produced are defects in the machinery that reports on plan quality, which is the
least instrumented surface in the pipeline.

## Evidence

- aspect: artifact_consistency — `footprint_resolved: false`, 2 of 6 checks `inconclusive`
- aspect: execution-context-dispatch-audit — `shape_violation: unmeasurable`, `surface_b_resolve_target_entries: 0`
- aspect: routing-decisions — `mis_prune:sonar-roundtrip` fail, adjudicated `rejected_as_misattributed` against `decision.log` entry `9e1b0f`
- aspect: script_failure_analysis — 6 unique findings, 3 miscategorised
