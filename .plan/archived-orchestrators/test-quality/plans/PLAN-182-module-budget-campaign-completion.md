# PLAN-182: Module-Budget Campaign Completion

epic: test-quality
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-182-module-budget-campaign-completion.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> **Supersession: this spec REPLACES PLAN-140 wholesale.** PLAN-140's run model
> (module-budget-campaign-runs-2-7) is folded here in full — the operator-directed
> carve campaign to completion (operator order 2026-09-22): full campaign, not a
> slice remainder. PLAN-140 transitions to `superseded` at this spec's emission;
> nothing it still claims is left orphaned.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode):
process compliance is mandatory, not advisory. Every emitted `/plan-marshall` command
carries the standing process-compliance trailer.

## Objective

Drive the module-budget campaign to **completion** — the epic's one structural rule
(`test-module-line-budget`, 400-line module budget) reading **zero over-budget modules
tree-wide at the final landing** — across the entire remaining campaign surface:
the **B0 carve campaign** (carves 3–12 of the 12-source run-3 list, one distinct
source per PR), the **B1 cluster splits**, the **B2 doctor-drain reduction**, the
**B3 rule-set flip-to-error**, the **B4 glob reductions**, and **runs 4–7** (slices
`030`, `070`, `080` and the `rule6` glob). Done when the doctor's whole-tree sweep
reports no module over budget on the rule at the merge HEAD and every slice this
campaign owns reads at or under 400 lines.

⚠️ **This is a completion contract, not a single carve.** Like PLAN-140 before it
(unlike PLAN-181's single-source carve), it stages at most ONE emission at a time and
harvests the campaign slice-by-slice. Each emission is its own PR. The budget figures
in this epic's ledger are **stale on arrival** — every transcribed population moved in
every recent window (12-source/279→306 saw four firings) — so D1 re-derives before
every emission.

## Deliverables

1. **D1 — Re-derive the whole campaign surface at dispatch.** ⛔ **Gating.** The
   ledger's 12-source B0 list, its 61-module over-budget population, and each
   slice's per-source module paths are ALL LEADS — populations moved +35 (+27 budget,
   +9 docstring, +2 preamble, +1 subprocess-pythonpath) in the last measured window
   alone accruing entirely to other epics' landings. Re-count from the doctor's own
   sweep at dispatch HEAD before ANY sizing; do not adopt nomination figures.
   *Done when:* the over-budget source list, its per-source module pathschers, and the
   campaign's slice ordering are each re-derived at dispatch and matches the
   nomination shape or the deviation is recorded with cause.
2. **D2 — Carve emissions 3–12 (B0), one source per PR, sequentially.** Mirror the
   PLAN-181 carve shape: per-source fixture hoists (`_*fixtures.py` outside
   collection), repeated setup replayed statement-for-statement, over-budget modules
   split into `test_*` collection units. **N=1 sequential:** each PR lands and is
   reconciled before the next carve is emitted; never more than one carve in flight.
   *Done when:* every source in the re-derived B0 list ships as its own carve PR with
   no behavioral change and every module in scope reads ≤400 lines.
3. **D3 — B1 cluster splits.** After B0 lands, split the B1 over-budget modules that
   the cluster-split horizon names (per the epic's B1 surface partition), one cluster
   per emission. *Done when:* every B1-split module reads ≤400 lines with assertions
   intact.
4. **D4 — B2 doctor-drain reduction.** Drain the doctor's over-budget residue so the
   rule population drops below its flip threshold. *Done when:* doctor error-0 on the
   rule at merge HEAD with the budgeted population down by the scoped modules.
5. **D5 — B3 flip-to-error + B4 glob reductions.** Flip the module-budget rule from
   `severity: warning` to `error` (three-recorded-firings precedent: the drift has a
   named instance record) and reduce the B4 glob carves. *Done when:* the flip is in
   at `severity: error` and every remaining carve in the glob works against the
   no-grow floor.
6. **D6 — Runs 4–7 (slices `030`, `070`, `080`, `rule6`).** Execute the remaining
   campaign runs, each sliced per the PLAN-140 run model, slices measured against the
   budget (not a line target). *Done when:* each slice's over-budget count is reported
   before and after, zeroing toward the whole-tree completion verdict.
7. **D7 — Fidelity proof on every emission.** `_fidelity_diff` before/after on each
   carve/split commit: test_identities unchanged, lost=0/gained=0, duplication + banner
   reports with introduced=0. *Done when:* the reports are attached to each carve PR
   with clean verdicts.
8. **D8 — Whole-tree completion + doctor clean.** The campaign's terminal gate:
   whole-tree `test-module-line-budget` over-budget count **0** at the merge HEAD,
   `pytest` green both orders, no new skips, doctor 0-errors. *Done when:* the
   completion verdict is attached with the measured count.

## Expected Surface

- OBSERVED: the campaign's owned surface is the over-budget module population under
  `marketplace/bundles/{bundle}/skills/*/test/` re-derived at D1; B0 sources are the
  12-source run-3 list, B1–B4 and runs 4–7 per the PLAN-140 run model. The epic's
  rule population figures are LEADS and are re-derived, never transcribed.

## Dependencies and Sequencing

- Depends on: carve 2 (PLAN-181, landed #1582) — the carve template; the
  `addition-based` split instruments (PLAN-105, landed); the fidelity instruments
  (PLAN-105/PLAN-170, landed).
- Supersedes: **PLAN-140 wholesale** (transport to `superseded` at emission — its
  run-2..7 model is carried here in full; no orphaned claim).
- Sequencing: **N=1 sequential, one emission in flight** — each carve lands and is
  reconciled before the next is emissioned. Never emits into a slot while a live
  plan's gate is red (flight-line discipline); emit only on the operator's running
  queue order or into a free slot.
- Pairs with: PLAN-183 (carried defects + watches closure) — disjoint surface
  (PLAN-182 = module budget in WS-04; PLAN-183 = production/harness defects +
  watches in WS-03).
- Ordering note: B0 → B1 → B2 → B3 → B4 → runs 4–7, per the campaign's staged
  discipline; each step's size re-derived at its dispatch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-182-module-budget-campaign-completion.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It
creates and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and
reports its outcome through its PR and its inbox message. Each carve report carries a
complete `landing-facts` block; narrative-only landings cost a hand-recovery drain
every time. The inbox exception's qualifiers and the sole sanctioned write mechanism
are stated in `persona-plan-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
