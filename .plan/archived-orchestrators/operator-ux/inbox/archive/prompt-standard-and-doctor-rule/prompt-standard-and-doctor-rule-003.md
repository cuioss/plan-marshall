envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T13:41:15Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=prompt-standard-and-doctor-rule
recurrence_of=2026-08-25-09-002

# Stamp returned_with_findings when a self-review round loops back with findings

## Context

**Second independent instance.** Active global lesson `2026-08-25-09-002` recorded this exact defect on 2026-08-25 and is still unapplied — this plan's own `project:finalize-step-lessons-housekeeping` step reviewed and retained it on 2026-09-01 with the note *"returned_with_findings stamping - dispatcher outcome vocabulary untouched by this plan, no coverage"*.

This run reproduces it with fresh numbers. The `6-finalize` dispatch-boundary ledger holds 11 rows: 7 `step_complete`, 3 `error`, 1 `blocked_user_review`. All three `error` rows are `pre-submission-self-review` rounds that examined their surface, filed findings, and had those findings fixed and landed (`b0bdf820`, `c713b570`, `a9cbdbb0`). They carry **534,565 tokens — 33.9% of the phase's dispatch-boundary total**. `returned_with_findings_count` is `0` in every phase of this plan.

`plan-retrospective/references/logging-gap-analysis.md` defines `error_total_tokens` as the spend on dispatches that are *"genuinely non-productive: they raised a fatal error and returned nothing (findings-bearing loop-backs are now stamped returned_with_findings, not error, so what remains under error is genuine terminal waste). This is the figure a reader acts on."* A reader acting on this plan's figure concludes 534K tokens bought zero detection. Those rounds are where all eleven of the run's in-house defects were caught.

## Root cause

`returned_with_findings` is stamped by the finalize dispatcher only when a dispatched step's `mark-step-done` recorded `outcome: loop_back`. `pre-submission-self-review.md` mandates `--outcome failed` on a findings-bearing round (line 429, gating-step convention shared with `pre-push-quality-gate`), and its § "How this is recorded" states explicitly that it introduces **no** new outcome. The productive-loop-back cause is therefore structurally unreachable for the highest-re-firing step in the finalize lane, and every one of its productive rounds falls through to `error`.

## Proposed action

Either make a findings-bearing self-review round stamp `outcome: loop_back` (with `--loop-back-target 6-finalize`, the inline-replay target it already uses in practice), or widen the dispatcher's `returned_with_findings` trigger to cover a `failed` outcome from a step that persisted findings in the same round. Reserve `error` for a dispatch that could not complete its examination.

The same conflation appears one tier down and one tier up on this plan, so the fix should be checked against both: `status.metadata.phase_steps` records `prior_firings: [failed, failed, failed, failed]`, which cannot distinguish *"found defects"* from *"could not look"*; and the phase-5 `record-step` row for `verify:coverage` reads `outcome=error` for an inline attempt killed at 388s by the Bash ceiling — an infrastructure event, not a defect.

## Evidence

- aspect: logging_gap_analysis — `6-finalize` distribution `3 error, 7 step_complete, 1 blocked_user_review, 0 returned_with_findings`; `error_total_tokens: 534565`, `retryable_total_tokens: 0`
- aspect: plan_efficiency — the same 534,565 is 33.9% of `dispatch_boundary_total=1578291`
- qgate findings `7d498d` `50fca1` `8562ca` `304fde` `45f9f0` `977805` `4804a5` `276d72` `26b0bb` `ebbf9b` `e8b128` — all eleven resolved `fixed` with landed-commit evidence
- decision `35b0d6` / `record-step` entry `e5f7d8` — the phase-5 `verify:coverage` ceiling kill recorded as `outcome=error`
- prior instance: global lesson `2026-08-25-09-002` (active, unapplied), decision `248452` (retained by this run's housekeeping)
