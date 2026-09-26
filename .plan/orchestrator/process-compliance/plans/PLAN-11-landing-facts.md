# PLAN-11: Landing-facts enforcement

> ⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision relayed in inbox `review-apparatus-001`).** Parked.
> Do NOT emit; un-park only by explicit operator decision. The implementation-independent content of this spec
> (rules, invariants, fixtures) is extracted to
> `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/process-compliance-carry-over.md`. The body below is kept
> intact as the evidence chain.

epic: process-compliance
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-11-landing-facts.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make unfactored landings impossible. The emit-landing finalize step writes the narrative
but not the machine-readable facts block on at least one path, so drains pay hand-recovery
for every required fact: 9 of this epic's own 13 drained landings carried narrative only,
and the test-quality drain paid the same recovery on two foreign landings. This plan wires
the facts block into the emit path atomically, gates filing on `landing-check`
completeness, and records the CI-wait suppression hints that landed alongside the evidence.

## Deliverables

1. Emit-landing contract fix: the facts block is written atomically with the narrative
   on every emit path (no narrative-only filing).
2. File-time gate: a `landing-check complete: false` at file time blocks filing (or
   records an explicit exemption) instead of staying silent until the drain pays for it.
3. Backfill accounting: the 9 narrative-only landings already reconciled get a BBM-style
   verification note so the gap between required-facts-drained and nothing-outstanding
   is visible, not assumed.
4. CI-wait suppression hints: transient wait-budget/CI-timeout suppressions recorded as
   preference hints with recurrence evidence (the phase-gates 2/2 precedent), not as
   silent drops.

## Claim Labels

- OBSERVED: both PLAN-180 carve-1 landings carried narrative only; `landing-check` returned complete:false with 9-of-9 missing keys on each — read at `.plan/orchestrator/process-compliance/inbox/test-quality-001.md` § What was observed
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite landing bodies not opened
- OBSERVED: the drain corroborated merge facts independently (the hand-recovery the block exists to remove); same pre-fix class as two earlier landings — read at `.plan/orchestrator/process-compliance/inbox/test-quality-001.md` § Cost paid
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite history needs plan-store read
- OBSERVED: the emit-landing step writes narrative but not facts on this path; a file-time complete:false is currently silent — read at `.plan/orchestrator/process-compliance/inbox/test-quality-001.md` § Suggested direction
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite path behavior needs outline
- OBSERVED: 9 of this epic's 13 drained landings were narrative-only (4 complete) — drain-proposal tally, corroborated by two inline `landing-check complete: true` spot checks
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: tally plus spot checks population not reopened
- OBSERVED: 2 identical `[ci_timeout]` findings suppressed after the terminal precondition showed green (recurrence 2/2) — read at `.plan/orchestrator/process-compliance/inbox/phase-gates-010.md` § body
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite suppression history not reopened
- HYPOTHESIS: the wait-budget lapse on a live-pending finalize is the same wait-artifact class — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` § wait-budget seam (verify-at-outline; folded lead from `compliant-paths-006.md`)
  - verdict: corroborated | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: wait budget key read default present
- Verify-first clause: the consuming phase settles the HYPOTHESIS clause against the implementing source before scoping — refutation loops back to re-scope
  - verdict: unverifiable | checked_at: e995df45ce86e76575106d323602e1d58906bda8 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction no source check

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `landing-check` gate seam lives here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — emit-landing step lives here
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — landing-check regression tests live here
- OBSERVED: `test/plan-marshall/phase-5-execute/` — adjacent finalize coverage lives here
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` § emit-landing step file — exact emit file (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-07 surfaces (shipped, no live collision); PLAN-08 (shared orchestator surface area — sequence, do not parallelize); PLAN-12 (`branch-cleanup.md`, discovered when PLAN-12 folded new material — confirmed via `corpus cross-check` — sequence, do not parallelize); PLAN-13 (this spec's bare-directory `phase-6-finalize/` declaration covers every file PLAN-13 names — `SKILL.md`, `archive-plan.md`, `dispatch-inline-split.md`, `emit-landing.md`, `create-pr.md` — discovered when PLAN-13 was staged; sequence, do not parallelize)
- Adjacent to: test-quality epic (foreign landings stay owned there — this plan fixes the producer contract, not their ledger)

## Folded inbox material (same act)

- `test-quality-001.md` (finding): missing facts blocks, hand-recovery cost — head of this spec
- `phase-gates-010.md` (candidate-lesson): CI-timeout suppression hint — folded; expected surface unchanged by this fold (preference hint, adds no file surface — recorded explicitly)
- `phase-gates-011.md` (candidate-lesson): spend-cap suppression recurrence — folded as recurrence of the same hint; expected surface unchanged (recorded explicitly)
- `compliant-paths-006.md` (candidate-lesson): wait-budget lapse hint — folded; expected surface unchanged by this fold (hint, adds no file surface — recorded explicitly)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-11-landing-facts.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
