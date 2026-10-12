envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T20:00:36Z

# Re-gate pre-push-quality-gate on the phase-5 build verdict before running it

**Component**: `plan-marshall:manage-execution-manifest` (compose), with `plan-marshall:phase-6-finalize` (pre-push-quality-gate) as the consumer
**Category**: improvement
**Confidence**: high
**Signal source**: plan-retrospective (request-result alignment, plan efficiency, logging gaps), plan-38-review-bot-re-review

## Context

This plan changed one value in `.plan/marshal.json`. That file is not buildable, and the spec said the Maven gates have nothing to build and must be reported as not applicable. The phases handled this differently:

- **Phase 5 got it right.** `build-decision quality-gate` returned `not_necessary` because the plan footprint touches no build_map glob. Both verification steps were recorded as skipped.
- **Finalize still built.** `pre-push-quality-gate` ran a whole-tree `verify -Ppre-commit` with 171 tests, taking about 172s.
- **The decision log explains why.** At phase-4 compose the manifest "kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed".

## Root cause

The manifest decides whether to keep the gate at phase 4, before the worktree exists, so it can only fail open. Nothing re-checks that decision once phase 5 has set the footprint and the build verdict, and the gate step does not check them itself.

## Proposed action

Before `pre-push-quality-gate` runs, have the gate step (or a manifest re-evaluation at the start of finalize) read the settled build-decision for the realized footprint. When the verdict is `not_necessary`, record the step as skipped with that reason instead of running a whole-tree build. Also make the in-process build write a change-ledger row: this build left none, so the retrospective reports build_time as unavailable for a plan that did build.

## Evidence

- decision.log 17:41:55: `pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict`
- decision.log 17:45:56: `Final quality sweep skipped — build-decision quality-gate returned not_necessary`
- work.log 17:48:36–17:52:12: pre-push-quality-gate ran Maven twice, the second time after an argparse rejection of `maven resolve-test-scope`
- plan_efficiency: build_time is `unavailable`, because the ledger holds no build row

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-38-review-bot-re-review-005.md` from plan plan-38-review-bot-re-review (PLAN-38, #24)
