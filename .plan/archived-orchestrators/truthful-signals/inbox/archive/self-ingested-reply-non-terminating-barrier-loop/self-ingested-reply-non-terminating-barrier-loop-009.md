envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:18:53Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# dispatch_coverage_violation has no carve-out for the one documented hybrid step

## Observation

`dispatch-inline-split.md` classifies `default:architecture-refresh` as **DISPATCHED**, and its own roster row explains why the classification is partial:

> hybrid, classified dispatched: its Tier 0 discover + diff is deterministic inline script work, and its **Tier 1 re-enrichment fans out** under `phase-6-finalize` per affected module. The dispatching tier governs the classification, so the step carries exactly one roster row.

`execution-context-dispatch-audit.md`'s `dispatch_coverage_violation` rule then says: any step the roster classifies DISPATCHED that reaches a terminal `outcome` with zero matching `[DISPATCH]` line is a finding.

On this plan, `architecture-refresh` reached `outcome=done` with zero `[DISPATCH]` lines — correctly, because `decision.log` 08:03:22Z records **"Tier 1 skipped - change_type = bug_fix"**. Only Tier 0 ran, and Tier 0 is documented inline work. Running inline was the right behaviour, and the rule as written flags it as an `error`-severity hard-rule violation.

## Why it matters

Tier 1 is gated on `change_type`. Every plan whose `change_type` is not `feature` — every `bug_fix`, `tech_debt`, `analysis`, `verification` plan — will skip Tier 1 and produce this false `error`. A detector whose false-positive rate is "most plans" trains readers to ignore its output, which is exactly how a real `dispatch_coverage_violation` gets missed.

This is the inverse failure of the sibling `shape_violation` defect: one check can never fire, the other fires when it shouldn't. Both live in the same aspect.

## Corrective rule

The roster must express the conditional, and the detector must read it. Concretely: mark `default:architecture-refresh` as **conditionally dispatched** in `dispatch-inline-split.md` (dispatch expected only when its Tier 1 gate fires), and have `dispatch_coverage_violation` suppress the finding when the step's own decision-log line records the gate as not fired. A hybrid step whose dispatching tier is gated is not the same assertion target as an unconditionally-dispatched step.

## Evidence

- `phase-6-finalize/standards/dispatch-inline-split.md` § Dispatched steps, `default:architecture-refresh` row.
- `standards/execution-context-dispatch-audit.md` § Detection Logic, `dispatch_coverage_violation` row.
- This plan's `decision.log`: `08:03:15Z Tier 0 - .plan/project-architecture clean after discover, no commit needed`; `08:03:22Z Tier 1 skipped - change_type = bug_fix`.
- This plan's `status.metadata.phase_steps["6-finalize"]["architecture-refresh"]`: `outcome: done, display_detail: no module structure changed`.
