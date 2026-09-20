envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:34:11Z

# Bound the cost of re-firing finalize steps against the plan token anchor

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium

## Context

The plan consumed 4,063,723 tokens. Its calibration row is `multi_module + feature`, anchored at 1.5M warning / 2.5M error. The plan landed at **1.63x the error column**. Worked time was 154.3 minutes against the same row's 120-minute warning column.

6-finalize alone accounts for 1,944,394 tokens — 48% of the plan — across 26 configured steps. The step firing record shows: `pre-submission-self-review` 3 recorded firings after 2 failures (a 5-round convergence, 3 -> 4 -> 3 -> 1 -> 0 findings), `ci-verify` 3 firings, `automatic-review` 2, `sonar-roundtrip` 2, `project:finalize-step-plugin-doctor` 2, `push` 2, `adr-propose` 2, plus 2 loop-back iterations.

For comparison, 5-execute — where the actual implementation happened — consumed 620,880 tokens, under a third of finalize.

## Root cause

No finalize step carries a cumulative-spend ceiling, and no step's re-fire decision consults the plan's remaining budget against its anchor. A converging review loop is therefore unbounded in cost: each round is individually justified (the self-review really was still finding defects, and the loop really did converge to zero), but nothing observes that the aggregate has passed the error anchor.

The overrun is also invisible while it accrues. `metrics.md` renders the 6-finalize row as zero until an accumulator reconcile runs, and the anchor comparison happens only here, in the retrospective, after the plan has merged.

## Proposed action

Publish per-step firing counts and cumulative token spend against the plan's `(scope_estimate, change_type)` anchor as finalize proceeds, so the operator sees the budget position at each re-fire decision rather than afterwards.

Consider a soft gate: when cumulative spend crosses the warning anchor, a step's re-fire becomes an explicit operator decision rather than an automatic retry.

This is filed at medium confidence because the correct remedy is a design question — the loop converged and the defects it found were real, so simply capping the rounds would trade budget for quality. The finding is that the trade is currently made blind.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error finding, `multi_module+feature error at 2.5M tokens`, 4,063,723 observed; `max_phase_token_share: 0.48`, `dominant_phase: 6-finalize=1944394`
- aspect: plan_efficiency — worked time 154.3 min crossed the 120-min warning column
- `status.metadata.phase_steps` — the firing counts above; `loop_back_iteration: 2`
- 5-execute at 620,880 tokens vs 6-finalize at 1,944,394
