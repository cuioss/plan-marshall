envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:53:31Z

component=plan-marshall:phase-2-refine
category=improvement
title=A 100%-across-all-six-dimensions confidence score is flagged but has no mechanical way to be checked
confidence=medium
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding 30308c (2-refine)

# A 100%-across-all-six-dimensions confidence score is flagged but has no mechanical way to be checked

## Context

Post-clarification re-analysis scored all six confidence dimensions at 100 (correctness, completeness, consistency, non-duplication, ambiguity, module-mapping), lifting the plan from 49.0% to 100.0% in one operator round. The phase-2-refine Step 13 Confidence Justification check flagged it rather than accepting it silently — which is the check working as designed.

## What makes this a candidate rather than a non-event

The flag is the right behaviour, but the check has **no mechanical discriminator** between the two cases it must separate:

- A genuine 100%: a fully-resolved operator round that actually closed every open gap.
- A self-graded 100%: the scorer marking its own work, where a uniform perfect score is a symptom of not looking rather than of having looked.

Both produce the identical artifact — six 100s and a justification paragraph. The check can only surface the score and ask an LLM to justify it, and an LLM justifying its own score is not independent evidence.

## How this instance was resolved (and why the resolution is the interesting part)

The disposition did not wave it through. It recorded that the score was checked against **downstream evidence rather than self-assertion**:

- The operator personally answered all four clarification questions (D0/D3 rescope, D1 dual-home authorship, D4 dual-skill split, lesson-id drop) — so the gap closure was real, not inferred.
- The substance was independently re-derived twice downstream: `phase-3-outline` re-ran the D0 population sweep, and the 3-outline Q-Gate pass re-derived it a third time. Both reproduced it exactly, **including corrections to two row-vs-file counts the original request had wrong**.

That last clause is the generalisable finding: the confidence score was validated by *later phases reproducing the same conclusion from scratch*, not by the refine phase's own reasoning. Downstream reproduction is the only independent evidence available for a self-graded score.

## Proposed action

- Have the Confidence Justification check name the **evidence class** its justification rests on — `self-assessment`, `operator-answered`, or `downstream-reproduced` — rather than accepting free prose. Only the latter two are independent.
- Consider deferring the check: a 100% score at refine time cannot be validated at refine time. A retrospective-band re-read that asks "did any downstream phase contradict the refine-time confidence?" has evidence the refine-time check structurally cannot have.

## Evidence

- Q-Gate finding `30308c`, phase `2-refine`, type `triage`, resolution `taken_into_account`.
- Work log: `aggregate-confidence` 49.0 at 12:14:10, 100.0 at 12:48:21, with four baked-in clarifications recorded at 12:47:53.
