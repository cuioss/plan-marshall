# PLAN-10: `end-phase` Overwrites Instead of Accumulating, Silently Corrupting the Measurement Corpus

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

A loop-back re-runs `end-phase`, which **replaces** rather than accumulates a phase's token
attribution. On one observed plan **73 % of phase-5's token attribution vanished** — and the rendered
`metrics.md` still displays the *pre-corruption* figure, so the loss is invisible at the reporting
surface.

⛔ **This is the highest-severity item forwarded into this epic, because it corrupts the substrate
every other measurement reads.** Every looped-back plan in the archived corpus is understated **by
construction**, and loop-backs are common — two of one window's four plans looped back.

## Deliverables

1. Make phase-token attribution accumulate across re-entry instead of replacing, so a loop-back adds
   to the phase total rather than discarding what preceded it.
2. Make the corruption visible where it is read: `metrics.md` must not render a stale pre-corruption
   figure. A phase whose attribution was re-entered is reported as such.
3. Assess corpus damage: how many archived plans are understated, and by how much. ⛔ **Report the
   affected count SEPARATELY from the number of plans examined** — volume-read-as-coverage is a
   recorded recurring archetype here and this deliverable is exactly where it would recur.
4. A regression test that loops a phase back and asserts accumulation, not replacement.

## Claim Labels

- **HYPOTHESIS (forwarded lead, NOT orchestrator-verified)**: `end-phase` is replace-not-accumulate
  and one plan lost 73 % of phase-5 attribution. Source: `exploration-share-is-unmeasured-007` via
  `truthful-signals-003`, origin PLAN-99 / PR #1043. ⛔ **This orchestrator did NOT read the
  implementing code.** Confirm/refute at the `end-phase` implementation in
  `marketplace/bundles/plan-marshall/skills/manage-metrics/` § the phase-close write path
  (verify-at-outline). **Do not scope until the write path is read.**
- **HYPOTHESIS (derived)**: therefore every looped-back plan in the corpus is understated. This
  follows from the mechanism, not from a corpus survey — deliverable 3 is what turns it into a
  measured claim. ⚠ Do not state it as fact before then.
- **OBSERVED (corroborating, orchestrator-verified in a different context)**: the measurement surface
  demonstrably reports confident wrong numbers — #1040's retrospective reported `recall 0%, all 7
  declared files missing` while squash commit `8b143643b` touches exactly those 7 files. That is a
  *different* defect (PLAN-CIS-012's) but it establishes that this surface does produce confidently wrong
  figures, so a second such claim is plausible on its face.
- **Verify-first clause**: `metrics.md` showing the pre-corruption figure is the load-bearing half —
  it is what makes the loss invisible. Verify the render path separately from the write path; they
  may be the same defect or two.

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the `end-phase` write path and the `metrics.md` render (verify-at-outline)
- **OBSERVED**: `test/plan-marshall/` — regression test
- **Adjacent, NOT touched**: `plan-retrospective` (PLAN-CIS-012/PLAN-CIS-013's surface) reads this data but does not write it

## Dependencies and Sequencing

- **Depends on**: none. ⭐ **Independently runnable today** — it is one of only two plans in the epic
  with no gate in front of it.
- ⛔ **BLOCKS PLAN-CIS-012's D5 blast-radius read and every cross-plan token-economics conclusion.**
  Until this lands, D5 would measure a corpus that is still being actively corrupted. This is the
  forwarded cluster's explicit sequencing consequence and it is the strongest argument for running
  this plan early.
- ✅ **Surface-disjoint from PLAN-01** (`manage-metrics` vs `manage-architecture` /
  `tools-marketplace-inventory`) — the two may run concurrently.
- ⚠ **Cross-epic check owed before emitting**: `truthful-signals` has launched plans touching
  `phase-6-finalize` and the manifest surface. Confirm none touches `manage-metrics`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-10-end-phase-replace-not-accumulate.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write.
