envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T08:57:36Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# Stamp returned_with_findings when a self-review round loops back with findings

## Context

The 6-finalize dispatch-boundary ledger records 13 rows. Ten are `step_complete`; three are `error`, carrying 679,275 tokens — 19% of the phase's whole 3.57M spend. All three `error` rows are `pre-submission-self-review` rounds that examined their surface, filed findings, and had those findings fixed: `status.json` shows `prior_firings: [failed, failed, failed]` before the fourth round closed `done`, and decision `fae1f5` records round 2's findings driving a convergent narrowing fix. Round 4 examined 301 candidates.

`returned_with_findings_count` is `0` in every phase of this plan.

`logging-gap-analysis.md` defines `error_total_tokens` as the spend on dispatches that are "genuinely non-productive: they raised a fatal `error` and returned nothing (findings-bearing loop-backs are now stamped `returned_with_findings`, not `error`, so what remains under `error` is genuine terminal waste). This is the figure a reader acts on."

A reader acting on this plan's figure would conclude 679K tokens bought zero detection. The opposite is true: those rounds are where the run's real defects were caught, including a correctness bug in `_raw_mentions_module` that demoted `not_derivable` to `unclaimed` — the exact merge the tool exists to prevent.

## Root cause

`returned_with_findings` is stamped by the finalize dispatcher only when a dispatched step's `mark-step-done` recorded `outcome: loop_back`. `pre-submission-self-review` stamps `outcome: failed` on a findings-bearing round. The productive-loop-back cause is therefore structurally unreachable for the highest-re-firing step in the finalize lane, and every one of its productive rounds falls through to `error`.

## Proposed action

Make a findings-bearing self-review round stamp `outcome: loop_back` rather than `failed`, so the dispatcher reaches `returned_with_findings`. Reserve `failed` / `error` for a round that could not complete its examination.

Keep the two distinguishable at the step level too: `prior_firings: [failed, failed, failed]` currently cannot tell "found defects" from "could not look", which is the same conflation one tier up.

## Evidence

- aspect: logging_gap_analysis — 3 `error` rows / 679,275 tokens; `returned_with_findings` 0 plan-wide
- aspect: log_analysis — `6-finalize.error_total_tokens: 679275`, `returned_with_findings_count: 0`, `retryable_total_tokens: 0`
- aspect: plan_efficiency — the same 679K is 19% of the dominant phase
- decision `fae1f5` — round-2 findings are real and drove a convergent fix, not a failure
