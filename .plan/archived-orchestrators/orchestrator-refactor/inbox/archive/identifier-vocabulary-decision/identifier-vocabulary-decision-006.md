envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:25:01Z

component=plan-marshall:plan-retrospective
category=bug
title=Step 2.5 metrics reconcile is inert when no phase accumulator file exists

# Step 2.5 metrics reconcile is inert when no phase accumulator file exists

## Context

`plan-retrospective/SKILL.md` Step 2.5 exists specifically to stop the plan-efficiency aspect reading an unclosed `6-finalize` as zero. It instructs the workflow to run `manage-metrics generate` so each phase's durable `work/metrics-accumulator-{phase}.toon` is folded into its row, giving `6-finalize` its accumulated floor rather than nothing. The step names the defect it closes: "R2: the retrospective reads an unclosed accumulator".

This run executed the reconcile as documented. `generate` returned `status: success` with `phases_recorded: 6`. The `6-finalize` row in the regenerated `metrics.md` still renders `-` for Worked, Reported, Idle, Tokens, Tool Uses and Billing. The totals remain `n=4/6` for tokens and worked time.

The reason is that the plan directory contains no `metrics-accumulator-*.toon` file for any phase. `collect-plan-artifacts` enumerated all 39 files; the `work/` directory holds `metrics-dispatch-boundaries-4-plan.toon` and `metrics-dispatch-boundaries-5-execute.toon`, and no accumulator file at all. There was nothing for `generate` to fold.

## Root cause

Step 2.5 assumes the durable per-phase accumulator exists. When no accumulator is ever written, `generate` succeeds, reconciles nothing, and the mitigation silently does not fire — leaving exactly the zero-reading R2 was written to prevent, with a `status: success` in front of it.

## Proposed action

Make the reconcile report what it folded. When `generate` finds no accumulator for a phase still listed in `phases_missing_end_time`, say so, so the retrospective can mark the phase's figures as unmeasured rather than presenting an empty row beside five populated ones. Pairing this with the finalize token-attribution fix (the `6-finalize` dispatch-boundary proposal) addresses the upstream cause; this proposal addresses the mitigation's own false-clean.

## Evidence

- aspect: plan_efficiency — `6-finalize` row renders `-` in every column after the Step 2.5 reconcile ran
- `manage-metrics generate` returned `status: success`, `phases_recorded: 6`, `phases_missing_end_time: [6-finalize]`
- `collect-plan-artifacts` 39-file manifest contains no `metrics-accumulator-*.toon` entry
- aspect: plan_efficiency — `totals_tokens_population_count: 4` of `totals_population_denominator: 6`
