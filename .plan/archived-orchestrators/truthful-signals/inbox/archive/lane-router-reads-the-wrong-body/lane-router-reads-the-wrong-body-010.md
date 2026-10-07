envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:56:42Z

component=plan-marshall:build-server-client
category=improvement
proposed_title=marshalld refused the raw submit with executor_mismatch while daemon_longpoll routing worked for every other build in the same run

# `marshalld` refused the raw `submit` with `executor_mismatch` while `daemon_longpoll` routing worked for every other build in the same run

# Status

Observed during `lane-router-reads-the-wrong-body`. Consequence: **`verify:coverage` was not run at all.**

## What happened

This plan edits the bundle that defines the executor. `marshalld` therefore refused a direct `submit` with `executor_mismatch` — **the anti-laundering wall working exactly as designed.** That refusal is correct and should not be weakened.

The problem is what it left behind:

- Inline execution of `verify:coverage` needs **~1387s** against a **600s** Bash ceiling — structurally unrunnable in-envelope.
- **Operator chose to skip coverage.** `quality-gate` and `verify plan-marshall` (13528 tests) were green; coverage was simply not measured.

## The asymmetry worth investigating

In the **same run**, every other build reached the daemon successfully via the wrapper's own routing seam — `mechanism=daemon_longpoll`. Only the **raw `submit` verb** refused.

So the executor-mismatch guard is applied at one entry point and not (or differently) at the other. Either:

- **(a)** the wrapper's routing seam is bypassing a guard the raw verb enforces — in which case the other builds in this run were laundered and the wall has a hole; or
- **(b)** the guard is correctly scoped and the raw `submit` is simply the wrong entry point for this case — in which case the workflow should route coverage through the same seam the other builds used, and coverage would not have been skipped.

**(b) is the benign reading and (a) is the alarming one, and the run does not discriminate between them.** That question should be settled before the next executor-touching plan.

## Why it matters

The visible outcome — "coverage skipped, operator decision" — reads as a clean, bounded tradeoff. The hidden caveat is that the skip may have been **unnecessary**: if path (b) holds, a working route to the daemon existed and was not taken. A correct guard produced a wrong operational outcome because the two entry points disagree.

## The rule (candidate)

1. **Determine whether the executor-mismatch guard is enforced at BOTH entry points** (`submit` and the wrapper's `daemon_longpoll` routing seam). If not, close the gap — in whichever direction the design intends.
2. **A long build that cannot run inline must have a documented route**, not an operator-judgement skip. `execution_tier: orchestrator` exists for exactly this; a step whose canonical command exceeds the Bash ceiling should hand off rather than be skippable.
3. Do **not** relax the anti-laundering wall. The wall was right; the routing around it was not.
