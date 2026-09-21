envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:05:33Z

# Candidate lesson: a build-daemon adaptive-budget TIMEOUT is not a red test — reading it as one manufactures a false failure

**Source**: PLAN-TRUTH-055 execution; 4 timeout events on a loaded machine
**Defect class**: confident-signal-hides-a-caveat / never-trust-a-routed-build's-outer-status
**Theme fit**: direct

## What was observed

The build daemon's **adaptive per-command budget** timed out four times on a loaded machine:

| Target | Timeouts | Elapsed |
|--------|----------|---------|
| whole-tree `module-tests` | 2 | 642 s each |
| `verify` | 2 | 330 s / 356 s |

The load-bearing fact: **the same targets had passed minutes earlier.** Nothing in the tree
changed between the green run and the timeout. The variable was machine load, which the adaptive
budget observes and mis-extrapolates from.

## Why this is a trap and not merely an annoyance

A timeout and a red test arrive through the same channel and can look alike at the outer status
layer. Reading a timeout as a test failure would have:

- manufactured a **false failing verdict** against code that had just passed;
- plausibly triggered a fix task against a non-existent defect;
- and, worse, made the eventual green look like the fix had worked — closing a phantom defect with
  a fabricated causal story.

This composes badly with the two standing rules already in the epic. "Never trust a routed build's
outer status — implausible duration is a failure signal" is *correct*, but its converse does not
hold: a **long** duration ending in a timeout is not evidence of a red test, and a short duration
is not evidence of a skipped run (a warm cache legitimately makes a gate 3 s). Both directions must
be verified **at the log layer** before concluding.

## Candidate rule

> A build result carrying a TIMEOUT status has produced **no verdict about the code**. It must be
> classified as `indeterminate`, never as `failed`. The only valid responses are: re-run, re-run
> with a larger budget, or report the indeterminacy — never "the tests are red".

> Before concluding anything from a build's outer status, read the LOG layer. The outer status
> conflates at least three distinct outcomes: tests failed, harness/daemon timed out, and wrapper
> exited 0 on failure (the known `build wrapper exit code misleading` defect).

> An adaptive per-command budget calibrated on an unloaded machine will time out legitimate work
> on a loaded one. The budget's own extrapolation is a **prediction**, and a prediction that fails
> is not a measurement of the code.

## Cross-reference

Same family as the standing `harness kills run_in_background jobs, zero output — NOT our bug` rule,
and the double-sampling rule from the plugin-registry marker survey: **a disagreeing pair is
`indeterminate`, NEVER `fail`.** This is the build-tier instance of that same principle, and the
generalization is now supported by three independent surfaces.
