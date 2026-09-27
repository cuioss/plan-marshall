# PLAN-12: Tool defect triage

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-12-tool-triage.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Triage four tool defects surfaced with reproduction evidence: `manage-status transition`
exiting 1 as a silent state-machine gap (the run continued past an un-transitioned phase),
the retrospective fragment pipeline failing as an exit-1 chain on missing fragment
files plus a stale `--output-file` call shape and doubled plan-dir resolution, a
`merge_lock` budget-reclaim `--hold-start` type mismatch (declared `float`, every caller
holds a wall-clock instant whose exact shape needs confirming), and a documented
argparse-recurrence signature (`--plan-id` router-scoped, must precede the verb token)
recurring anyway on a `ci` invocation. All four are small, bounded, and independently
reproducible — one triage plan, four defect closures with regression tests.

## Deliverables

1. `manage-status transition` silent-failure triage: reproduce the exit-1 path, capture
   stderr/exit context at the call site, route remediation (phase-guard precondition vs
   status document shape) explicitly — the run must fail loud, never continue past an
   un-transitioned phase.
2. Retrospective fragment-pipeline triage: stale `--output-file` shape corrected against
   `--help`, plan-dir resolved once without doubling, missing fragments handled as a
   structured skip rather than an exit-1 chain — with regression tests per defect.
3. `merge_lock` `--hold-start` type-mismatch triage: confirm the exact value shape every
   `--hold-start` caller passes (epoch float vs ISO-8601 string) against the argparse
   declaration at `merge_lock.py` and either correct the declaration or the callers, with
   a regression test pinning the agreed shape.
4. Argparse router-scoping recurrence triage: a `ci` invocation placed `--plan-id` after
   the verb token despite the documented recurrence signature at
   `tools-integration-ci/standards/pr-review-operations.md` § router-scoped `--plan-id` —
   reproduce the call shape that recurred and add the closed-vocabulary guard the
   persona-conduct lesson (PLAN-14 deliverable 4) names, or a script-side rejection
   message naming the documented fix, whichever closes the recurrence.
5. Regression tests locking all four fixes (silent-continuation guard, missing-fragment
   skip, `--hold-start` shape, argparse router-scoping recurrence).

## Claim Labels

- OBSERVED: `manage-status transition` exited 1 (script_internal_error, not argparse) and the run continued past an un-transitioned phase — read at `.plan/orchestrator/process-compliance/inbox/plan-02-worktree-discipline-010.md` § body
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite archived exit path needs reproduction
- OBSERVED: fragment pipeline emitted three script_failure markers (stale `--output-file`, doubled plan-dir, missing fragments file) while the step still completed done — read at `.plan/orchestrator/process-compliance/inbox/plan-07-opencode-repairs-007.md` § body
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite archived chain needs reproduction
- OBSERVED: work-log script_failure lines for check-artifact-consistency, collect-fragments, compile-report on 2026-09-21T01:17–01:20Z — cited at `.plan/orchestrator/process-compliance/inbox/plan-07-opencode-repairs-007.md` § Source
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: timestamps unopened
- Verify-first clause: the consuming phase reproduces both defects against the implementing source before scoping the fix — non-reproduction loops back to re-scope (downgrade to already-fixed with evidence)
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction no source check
- OBSERVED: `merge_lock.py` declares `--hold-start` as `float` (an epoch value; `math.isfinite`/`< 0` checks confirm numeric, not ISO-8601, parsing) while `branch-cleanup.md` documents binding `{hold_start}` to "the wall-clock instant of acquire" without stating epoch-vs-ISO-8601 — read at `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py`:1798,1806 and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`:104-108 (lesson 2026-09-20-08-014, folded from `lessons-handling-26-09-22-01-001.md`)
  - verdict: corroborated | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: merge_lock float epoch check prose shapeless
- OBSERVED: a documented argparse recurrence signature — `--plan-id` is router-scoped on the `ci` verb and MUST precede the first verb token — recurred anyway on a live invocation — read at `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md`:281 (lesson 2026-09-20-08-013, folded from `lessons-handling-26-09-22-01-001.md`)
  - verdict: corroborated | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: router scoped plan-id verbatim stated

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — transition seam lives here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — fragment-pipeline scripts live here
- OBSERVED: `test/plan-marshall/manage-status/` — transition regression tests live here
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` § fragment collection seam — exact file for the doubling/guard fix (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — `--hold-start` argparse declaration
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — `--hold-start` caller-side binding prose
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md` — documented router-scoping recurrence signature
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` § argparse router — exact seam for the recurrence guard (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-01 surfaces (manage-status, shipped — no live collision); PLAN-05/06 (shared tooling surface area — sequence, do not parallelize); PLAN-08 (`tools-integration-ci/scripts/ci.py`, `pr-review-operations.md` — confirmed via `corpus cross-check` — sequence, do not parallelize); PLAN-11 (`branch-cleanup.md`, from PLAN-11's bare-directory `phase-6-finalize/` declaration — sequence, do not parallelize)
- Adjacent to: automatic-review barrier machinery (stays untouched — this plan fixes silent tool failure, not review gating)

## Folded inbox material (same act)

- `plan-02-worktree-discipline-010.md` (candidate-lesson): transition silent-failure — staged as deliverable 1 of this spec
- `plan-07-opencode-repairs-007.md` (candidate-lesson): fragment-pipeline chain — staged as deliverable 2 of this spec
- `lessons-handling-26-09-22-01-001.md` (candidate-lesson): argparse/script-invocation recurrence pair (2026-09-20-08-014, 2026-09-20-08-013) — folded into deliverables 3-4; expected surface updated in the same act (+4 entries: merge_lock.py, branch-cleanup.md, pr-review-operations.md, ci.py hypothesis)
- `lessons-routing-002.md` (finding, relayed API-Sheriff cluster): five argparse shape recurrences across five scripts (unregistered verb, sibling-verb flag, router flag position ×2, abbreviated typed-ID, invented flag) + one exemplary compound-flag refusal — folded into deliverable 4 as class recurrences; expected surface unchanged by this fold (instances named as evidence, no new files claimed — recorded explicitly)
- `lessons-routing-003.md` (finding, relayed API-Sheriff cluster): review_completeness bare-bot recurrence (confirmed second instance — worked example owed at the barrier call site) + `qgate list` missing-required-`--phase` — folded into deliverable 4 as class recurrences; expected surface unchanged (recorded explicitly)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-12-tool-triage.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
