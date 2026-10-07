envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:42:46Z

# A fix's own rationale kept introducing the defect class it was closing

component: plan-marshall:phase-6-finalize
category: anti-pattern
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

This plan reproduced its own target defect repeatedly, in both phases:

- TASK-021 introduced the closed five-field enumeration that TASK-023 existed to remove.
- TASK-022 replaced an unreachable honest-degradation branch with an over-reachable
  one (a bare `status: error`), which finding 5ca1b4 then caught.
- TASK-020 widened 9 of 18 exit-code-convention carriers and broke 16 tests.
- Q-Gate c1cf3e: a transcribed-population fix introduced a new false population
  rationale — recorded as "the second time in this plan that a fix for transcribed
  populations introduced a new one".
- Q-Gate eadf9e: recorded verbatim as "the THIRD consecutive round in which a fix
  for a false population rationale wrote a new false claim into its own replacement".
- Q-Gate c78fef: the obvious replacement assertion was rejected mid-fix precisely
  because it was vacuous by construction — the archetype was caught only because
  the author checked.

## Root cause

Each fix authored a **new claim** to replace the false one, and the new claim was a
fresh opportunity to be wrong about the same population. The chain broke in exactly
the rounds where the remedy was DELETION plus delegation to an existing single
source (ced26f, eadf9e, 9dae3f, be6078) rather than a rewritten justification.

## Proposed action

Make deletion-and-delegate the default remedy for a false population or contract
claim, and require that any REPLACEMENT claim be accompanied by the independent
enumeration that grounds it. A rationale asserting a set property ("the ONLY flag
that...", "N sites carry this") must cite the derivation that produced it or be
removed instead of restated.

## Evidence

- Q-Gate findings c1cf3e, eadf9e (self-documented recurrence), c78fef (vacuous replacement refused)
- Q-Gate findings ced26f, 9dae3f, be6078 (deletion-and-delegate remedies that held)
- aspect: logging_gap_analysis — `pre-submission-self-review` fired 12 times, 5 `failed`
- status.metadata.phase_steps — `finalize-step-simplify` 9 firings, `pre-push-quality-gate` 8
