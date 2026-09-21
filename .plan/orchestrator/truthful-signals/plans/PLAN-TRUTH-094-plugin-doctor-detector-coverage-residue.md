> ⛔ **STAGED AT THE 2026-08-22 INGESTION — this plan closes REMEDIATION RESIDUE.**
>
> It exists because the gap-fix plans `500`/`510`/`520` ran **after** the epic audit closed, so every
> gap they filed, and every gap they left partially closed, is owned by no other staged plan. This was
> found by re-deriving ownership over the whole live gap set at ingestion: **218 gaps open, 38 unowned.**
>
> **Re-ground every gap below at HEAD before implementing it.** Its source is
> `cloud-runs/{NNN}-{slug}/gaps.md` in this ledger (git-ignored, ingested from `doc/plans/`), and a
> gap document is a snapshot. Line numbers in it are **leads, not addresses**; locate by quoted text.
> A gap that no longer reproduces is recorded as *already closed by `{sha}`* and **dropped, never
> re-fixed**.
>
> ⛔ **A run report is a dated record.** No deliverable here corrects one. Where a gap's `Where` names
> an archived `report-01.md`, the correction of record is the gap entry itself; only a live restatement
> is actionable, and it must be re-derived.

# Plugin-doctor detectors still report clean over populations they cannot reach

**Epic:** truthful-signals
**Branch prefix:** fix
**Source gaps:** `500/G1`–`G8` (`cloud-runs/500-plugin-doctor-detectors-report-clean-over-unexamined-populations/gaps.md`)

## Problem

Plan `500` (PR #1320) closed the *reports-clean-over-an-unexamined-population* class in three
plugin-doctor rules and **left it live in a fourth, inside its own Expected surface**.

`analyze_argument_naming` returns `[]` and the gate reports `findings: 0` whenever
`.plan/execute-script.py` is absent — **which is every cloud clone**. That silently disables the whole
`ARGUMENT_NAMING_*` cluster **including the rule plan 500 itself added**, and it renders *clean* rather
than *could not look*. The plan twice demanded that this coverage gap be "recorded, not asserted
clean"; its report never records it.

That is this epic's namesake defect, committed inside the fix written to remove it, at the fourth site
of four.

## Goal

No plugin-doctor rule can report a clean result over a population it did not examine. Where a rule
cannot reach its population, it says so in its own output, and a test proves the saying.

## Deliverables

**D0 — GATE: re-derive the rule population and the reachability of each rule's substrate.**
For every registered rule, determine what its population is and whether that population is reachable
in a clone with no `.plan/`. Publish two numbers: rules examined, and rules whose substrate can be
absent. *(closes no gap; gates D1–D5.)*

**D1 — `analyze_argument_naming` reports unreachability instead of cleanliness.** *(closes 500/G1 — high)*
When `.plan/execute-script.py` is absent the rule must emit a `could_not_look` signal the runner
renders, not an empty finding list. Pinned by a test that removes the executor and asserts the gate
does **not** read clean.

**D2 — the D1 anchor-vs-type-list control actually exercises `_scoped`.** *(closes 500/G2)*
The existing control never calls `_scoped`, so the mutation it exists to catch stays green. Rewrite it
as a matched pair and prove the negative control goes RED.

**D3 — publish `blind_spots` on a clean gate run.** *(closes 500/G7)*
The clean gate publishes population `152` but not `blind_spots` `69`. A population figure without its
blind-spot count is the same false-completeness signal one level up.

**D4 — bind the mutation register and the collateral list to a derivation.** *(closes 500/G3, 500/G6)*
§ Collateral omitted two landed files including a production change to `resolve_project_dir.py`, and
the mutation register's count is one low. Both must be derived at report time, not maintained.

**D5 — record the residue that was never written.** *(closes 500/G5, 500/G8)*
`500`'s § Residue is empty and two review findings (C4, C7) live only on a merged PR thread. Recover
them into the ledger and state the process rule that a disposition surviving only on a PR thread is
not recorded.

## Expected Surface

- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_argument_naming.py`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_runner.py`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py`
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/resolve_project_dir.py`
- `test/pm-plugin-development/plugin-doctor/test_analyze_argument_naming.py`
- `test/pm-plugin-development/plugin-doctor/test_runner.py`

## Out of scope

- Correcting any archived `report-01.md` under `cloud-runs/` — a run report is a dated record; see the
  banner. Where the same false claim is restated on a live surface, that restatement is in scope and
  must be re-derived rather than inherited from the gap's `Where` line.
- Any gap owned by another staged plan. Ownership was derived at ingestion; if a re-derivation shows
  an overlap, **record it and serialize**, do not silently absorb the sibling's gap.
- Re-fixing a gap that no longer reproduces at HEAD.

## Claim Labels

Every claim in this plan is **HYPOTHESIS** unless the deliverable marks it otherwise. The gap entries
it derives from were OBSERVED at their verification commit and re-checked at the 2026-08-22 ingestion,
but that check was per-gap and sampled, not exhaustive. **Treat every asserted absence as unverified
until the D0 gate re-derives it.**

## Verification

- The D0 gate publishes the population it examined **and** the count that reproduced, as two separate
  numbers. A zero must state which zero it is: *examined N, none reproduced* is a result; *could not
  look* is not.
- Every guard added or widened here is proved by a **matched positive/negative control** — a case that
  goes RED against the defect the guard names, and a near-identical case that stays green. A guard
  whose population can be empty publishes its population size on a clean run.
- No deliverable is reported complete on a read alone where the claim is about behaviour: execute the
  symbol, or mutate it and observe the red.

## Notes

**Derived figures are re-derived AFTER the review cycle closes, not before.** Both `500` and `520` had
their diff silently widened by CodeRabbit after their counts were taken, and `510`'s own participation
figure used a floating `origin/main` endpoint three sections after its own § Build gate corrects that
exact defect. The review is a diff-widening event. Take every count last.
