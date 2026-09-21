# PLAN-02: Make argparse rejections name their own fix

epic: finalize-machinery
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-02-invocation-surfaces.md` and is queued in the epic `status.json` `plans[]`
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

Retire the argparse-rejection class: nine rejections in one run across four signatures,
recurring from independent callers, including router-vs-verb flag splits and a
documented-safe flag that rejects. Ship rejection messages that name the offending flag
and the sibling verb to call, and repair the doc-vs-actual contract mismatches, so the
surface teaches its fix at the failure site.

## Deliverables

1. Rejection-message remedy: every signature in the class names the offending flag and
   the correct sibling verb/flag spelling at exit 2 (no docs-only fix).
2. Router-vs-verb splits repaired: ci pr prepare-body, github_pr --plan-id, and
   review_completeness --measured-diff-size accept-or-redirect consistently.
3. Doc-contract repair: automatic-review SKILL.md measured-diff-size safe-when-empty
   claim corrected to match the required-argument reality.
4. Regression evidence: each of the three recorded sites reproduces the old rejection
   and demonstrates the new message in one run.

## Claim Labels

- OBSERVED: nine argparse rejections in one run across four signatures, several recurring from independent callers — read at corpus lesson `2026-09-03-19-004` § `rejection class`
- OBSERVED: ci pr prepare-body router-vs-verb --plan-id split hit the orchestrator itself — read at corpus lesson `2026-09-03-19-003` § `router split`
- OBSERVED: --measured-diff-size is the one flag the empty-is-safe guarantee misses, now a documented-vs-actual mismatch at automatic-review/SKILL.md — read at corpus lesson `2026-08-25-09-014` § `doc contract`
- OBSERVED: manage-status read declares only --plan-id/--store and manage-plan-documents has no read verb, each hit more than once — read at corpus lessons `2026-09-03-11-004` § `status surface` and `2026-09-03-11-005` § `missing verb`
- OBSERVED: github_pr rejected --plan-id as the third recorded site of the class — read at `.plan/orchestrator/finalize-machinery/epic.md` § `defect 10`
- HYPOTHESIS: naming the flag and sibling verb in the argparse error path covers all independent callers without per-caller docs — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` § `argparse` (verify-at-outline)
- Verify-first clause: the consuming phase confirms the rejection sites against the implementing argparse sources before scoping; absence claims (a signature has no such trap) are verified exactly like presence claims. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — executor generation owning the invocation surface
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — status flag surface
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-plan-documents/scripts/manage-plan-documents.py` — missing read verb
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` — prepare-body router surface
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — plan-id rejection site
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — measured-diff-size doc contract

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-03 touches automatic-review scripts (review_completeness.py, bot_registry.py) while this plan touches automatic-review SKILL.md and the argparse sites — file-disjoint, may parallelize; sequence if either widens beyond declared files
- Adjacent to: WS-01 finalize ordering — no shared files

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-02-invocation-surfaces.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
