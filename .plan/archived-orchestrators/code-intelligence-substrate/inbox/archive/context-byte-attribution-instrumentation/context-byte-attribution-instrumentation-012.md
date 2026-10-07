envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:53:17Z

component=plan-marshall:phase-5-execute
category=bug
bundle=plan-marshall

# The orchestrator-tier yield boundary lets a task's own newly-authored tests ship unexecuted — and the one that did was wrong

## What happened

TASK-2 authored the tests for D1's `billing-composition` check. Its verification step required `module-tests plan-marshall`, which live-resolves to `execution_tier=orchestrator` at 766s — past the Bash ceiling. The leaf did the correct thing and yielded, logging at `2026-08-03T09:38:28Z`:

```text
[BLOCKED] (plan-marshall:phase-5-execute) TASK-2 verification needs module-tests
plan-marshall which live-resolves to execution_tier=orchestrator (766s over the
Bash ceiling). TASK-1 is complete and verified. TASK-2 file edits are complete
and lint-clean, with step 2 left un-finalized so the task is not falsely marked
done before its tests run.
```

That handling is exemplary — the task was deliberately left un-finalized precisely so it would not be marked done on unproven work. The orchestrator-tier run then came back (job `a40fafe5783042e2a3aad3be3f5deac4`, 359s): **14793 passed, 1 failed, 2 skipped. The sole failure was TASK-2's own newly-authored test.** Q-Gate finding `87d831` records it as *"written but never executed before the leaf yielded on the orchestrator-tier boundary, so it is unproven-not-regressed."*

## The structural finding

The guard that exists here protects the *task's completion status*. It does not protect the *test's execution*. Between authoring and the orchestrator-tier run, a test-authoring task's entire output is unverified — and the yield boundary is not a rare edge: any `module_testing`-profile task in a repo whose module-tests exceed the Bash ceiling hits it every time.

The gap is narrow but exactly wrong-shaped: a test-authoring task is the one kind of task whose deliverable **is** an executable assertion, so "edits complete and lint-clean" certifies nothing about the thing being delivered. Lint-clean on a test file means the file parses. It does not mean the assertion is true, or even that it says what its name says.

## What the unexecuted test actually got wrong

`test_metrics_blind_plan_floors_the_figures_it_contributed_to` looped over **all** figures. The contract it was testing (`audit.py` module docstring) says a figure any metrics-blind or partial plan **contributed to** is labelled `floor`, and `_bc_figure` implements that per-figure over its own contributor list. The blind fixture carries no payload-byte counters, so the four `byte_share_` figures have population 0 and correctly stay `label=measured` with value `n/a`.

**The assertion contradicted its own name** — the name says "the figures it contributed to", the loop said "all figures".

Fixed by scoping the floor loop to figures with `population > 0` (4 billing figures, non-vacuous) and adding the matched complement asserting the uncontributed figures keep `floor_population 0` and value `n/a`, so a block-wide floor would still fail.

## The through-line worth flagging to the epic

This is the **third** independent instance of one defect shape in this single plan. The two CodeRabbit catches on PR #1086 (routed separately) were both aggregations summing an unconstrained population. This test asserted a property over an unconstrained population. Same root, three surfaces:

> An assertion or aggregate was written against "everything" when the contract scoped it to a named subset — and in every instance the *numerator/predicate* was stated precisely while the *set it ranged over* was left implicit.

Two of the three were caught only by an external review bot; the third only by an orchestrator-tier test run that the authoring dispatch could not perform. **Zero of the three were caught by the authoring dispatch itself.**

## Solution

1. **Make "tests authored but not executed" an explicit, surfaced state** rather than an inference available only by reading the `[BLOCKED]` narrative. The task is correctly not-done, but nothing downstream can query *which* tasks carry unexecuted new assertions.
2. **Route a test-authoring task's verification through the scoped arm first.** The failing test lived in the audit package, where `497/497` runs in seconds. A package-scoped run inside the leaf would have caught this before the yield, at ~0 marginal cost; only the whole-module confirmation genuinely needs the orchestrator tier.
3. **Name-vs-assertion agreement is a self-review candidate class.** `test_..._the_figures_it_contributed_to` looping over all figures is mechanically detectable: a test whose name contains a restrictive qualifier but whose body has no corresponding filter. This pairs directly with the population-scoping candidate class proposed in the sibling message.

## Impact

Every `module_testing`-profile task in this repo, since whole-module tests here reliably exceed the Bash ceiling. The exposure is not the yield — the yield is correct — it is that the yield's window is where unverified assertions accumulate, and this plan proves the window is not empty.

**Note for the orchestrator-side pickup:** not present in messages 001-006. Consider merging the "shared shape" section with the population-scoping sibling message — they are one lesson observed from two surfaces, and the count of three-in-one-plan is the part that makes the case.
