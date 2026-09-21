envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:51:58Z

component=plan-marshall:phase-6-finalize
category=improvement
title=A finding raised at the self-review iteration ceiling cannot be fixed and re-reviewed within the run
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding 52ed98 (6-finalize, pre-submission-self-review iteration 3)

# A finding raised at the self-review iteration ceiling cannot be fixed and re-reviewed within the run

## Context

`pre-submission-self-review` ran three iterations — its ceiling. Iteration 3 surfaced one new finding (`52ed98`): the negative-control fixture-placement rationale is fully general but lives inside the narrower "Polarity trap in a hand-written ArchCondition" section, so an author of an ordinary `@ArchTest` rule following the binding-table row to the central doc gets no placement guidance.

The finding was **accepted rather than fixed**, with this rationale recorded verbatim: *"the fix would add prose that no review round examined — the exact failure mode this plan is about."*

## Root cause

The self-review loop has a fixed iteration ceiling. A finding raised **at** the ceiling has no remaining iteration to review its fix. The run then faces a forced choice between two bad options:

1. Fix it, and ship prose that no review round examined — manufacturing exactly the unexamined-green the loop exists to prevent.
2. Accept it, and ship a known under-specification.

This run chose (2) and documented why, which is the honest option. But the structural point stands: **the last iteration of a bounded review loop can only report, never remediate.** Its findings are systematically less likely to be fixed than findings from earlier iterations, and that bias is invisible in the aggregate "N iterations, M findings, all resolved" summary.

## Proposed action

Options, in increasing cost:

- **Report the bias.** Have the self-review step's `display_detail` / return payload distinguish findings raised at the ceiling iteration from findings raised earlier, so "clean" and "clean except for one ceiling-iteration finding we could not review a fix for" are not the same signal.
- **Allow a bounded fix-only iteration.** Permit one additional iteration whose scope is exactly the ceiling iteration's findings, reviewing only the fix diff rather than re-running the full candidate sweep.
- **Route ceiling findings to a follow-up by construction.** Rather than an `accepted` disposition with hand-written rationale, allocate a follow-up artifact automatically so the residue is scheduled rather than merely recorded.

## Why this belongs to `truthful-signals`

The confident signal here is "3 iterations, self-review clean". The caveat it hides is that the third iteration's finding was structurally unfixable within the run. The disposition was recorded honestly by this run — but only because the agent noticed. Nothing in the mechanism required it.

## Evidence

- Q-Gate finding `52ed98`, phase `6-finalize`, type `improvement`, severity `info`, resolution `accepted`, component `pm-dev-java:arch-gate-java`.
- Work log: `pre-submission-self-review` iterations at 14:28, 14:34, 14:40 (`iteration 3, 18 candidates examined, 1 new finding`); a fourth dispatch at 17:24 was a re-fire after loop-back, not a fourth review iteration.
- Cross-reference: this residue is also named in the plan's landing message (residue item 1).
