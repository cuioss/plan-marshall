# PLAN-12: Tool defect triage

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-12-tool-triage.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Triage two tool defects surfaced with reproduction evidence: `manage-status transition`
exiting 1 as a silent state-machine gap (the run continued past an un-transitioned phase),
and the retrospective fragment pipeline failing as an exit-1 chain on missing fragment
files plus a stale `--output-file` call shape and doubled plan-dir resolution. Both are
small, bounded, and independently reproducible — one triage plan, two defect closures
with regression tests.

## Deliverables

1. `manage-status transition` silent-failure triage: reproduce the exit-1 path, capture
   stderr/exit context at the call site, route remediation (phase-guard precondition vs
   status document shape) explicitly — the run must fail loud, never continue past an
   un-transitioned phase.
2. Retrospective fragment-pipeline triage: stale `--output-file` shape corrected against
   `--help`, plan-dir resolved once without doubling, missing fragments handled as a
   structured skip rather than an exit-1 chain — with regression tests per defect.
3. Regression tests locking both fixes (silent-continuation guard + missing-fragment skip).

## Claim Labels

- OBSERVED: `manage-status transition` exited 1 (script_internal_error, not argparse) and the run continued past an un-transitioned phase — read at `.plan/orchestrator/process-compliance/inbox/plan-02-worktree-discipline-010.md` § body
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite (plan-02-worktree-discipline-010); exit-1 behavior needs reproduction
- OBSERVED: fragment pipeline emitted three script_failure markers (stale `--output-file`, doubled plan-dir, missing fragments file) while the step still completed done — read at `.plan/orchestrator/process-compliance/inbox/plan-07-opencode-repairs-007.md` § body
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite (plan-07-opencode-repairs-007); run-behavior premise needs reproduction
- OBSERVED: work-log script_failure lines for check-artifact-consistency, collect-fragments, compile-report on 2026-09-21T01:17–01:20Z — cited at `.plan/orchestrator/process-compliance/inbox/plan-07-opencode-repairs-007.md` § Source
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: cited inbox Source timestamps; work logs not opened this pass
- Verify-first clause: the consuming phase reproduces both defects against the implementing source before scoping the fix — non-reproduction loops back to re-scope (downgrade to already-fixed with evidence)

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — transition seam lives here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — fragment-pipeline scripts live here
- OBSERVED: `test/plan-marshall/manage-status/` — transition regression tests live here
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` § fragment collection seam — exact file for the doubling/guard fix (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-01 surfaces (manage-status, shipped — no live collision); PLAN-05/06 (shared tooling surface area — sequence, do not parallelize)
- Adjacent to: automatic-review barrier machinery (stays untouched — this plan fixes silent tool failure, not review gating)

## Folded inbox material (same act)

- `plan-02-worktree-discipline-010.md` (candidate-lesson): transition silent-failure — staged as deliverable 1 of this spec
- `plan-07-opencode-repairs-007.md` (candidate-lesson): fragment-pipeline chain — staged as deliverable 2 of this spec

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-12-tool-triage.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
