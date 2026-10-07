# PLAN-01: Bind head-bound finalize steps to one anchor

epic: finalize-machinery
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-01-head-rearm.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode +
Muse Spark 1.3): process compliance is mandatory, not advisory.

## Objective

Retire the finalize re-fire loop: a HEAD move inside finalize currently re-arms every
head-bound step (one run fired the quality gate four times for three tasks), and the
pre-push gate certifies a tree review never sees because simplify advances HEAD after
certification. Ship a single pass anchor so head-bound steps certify the tree that
ships, with ordering or re-verification that makes the loop impossible.

## Deliverables

1. Single-pass HEAD anchor: head-bound steps (quality gate, simplify, ci-verify)
   certify or re-verify against one recorded anchor instead of live HEAD.
2. Step-ordering fix: pre-push-quality-gate vs finalize-step-simplify ordering resolved
   so certification covers the tree review sees (reorder or post-simplify re-gate).
3. Self-review placement resolved against simplify (lesson 2026-09-03-11-002): review
   runs on the final tree or its delta is re-checked.
4. Cost evidence: before/after measure of gate firings per finalize pass on a fixtures
   run demonstrating the loop is gone.

## Claim Labels

- OBSERVED: a HEAD move inside finalize re-arms every head-bound step — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` § `quality gate order`
- OBSERVED: the quality gate fired four times for three tasks in one run — read at corpus lesson `2026-09-03-19-005` § `re-arm mechanism`
- OBSERVED: pre-push-quality-gate is order 5 and finalize-step-simplify is order 8, and the gate certified 43ed295b while simplify advanced HEAD to 8827a7f2 — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/required-steps.md` § `step order`
- OBSERVED: finalize costs 3–5x execute with the gate as the dominant cost — read at corpus lesson `2026-09-03-11-007` § `cost symptom`
- HYPOTHESIS: a single recorded anchor plus a post-simplify re-verification closes the loop without cutting productive review rounds — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` § `re-entry check` (verify-at-outline)
- Verify-first clause: the consuming phase re-verifies the anchor mechanism against the implementing source (ci_verify / verdict_currency) before scoping; refutation loops back to re-scope. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — head-anchored verification
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — re-entry currency check
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — gate contract
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — simplify contract
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/required-steps.md` — step ordering
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` — self-review vs simplify placement

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-04 shares the phase-6-finalize standards directory but different files (ordering vs branch-cleanup) — sequence, do not parallelize, until this plan lands
- Adjacent to: WS-03 bot-currency work — a gate certifying the wrong tree cannot be fixed by review SHA comparison alone

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-01-head-rearm.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
