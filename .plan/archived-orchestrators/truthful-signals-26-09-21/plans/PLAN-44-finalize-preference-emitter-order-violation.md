# PLAN-44: preference-emitter Writes a Tracked File After the Merge Gate

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced by PLAN-40 (#981) finalize as a **real, verified contract violation**
> the executor refused to paper over — it left `.plan/project-architecture/default/enriched.json`
> uncommitted on main with the diagnosis rather than silent-revert / direct-commit / ignore.
> The **symptom** (dirty file) landed via **PR #984 (merged `ed248689e`)**; this plan is the
> **root-cause** fix. **Migrated from plan-optimization 2026-07-22** (successor epic; plan id kept).
>
> **Grounded at `main` @ `dfc4ac15c` (2026-07-22).** ⚠ The step `order` values below are from the
> PLAN-40 finalize report and are the D1 GATE's first thing to re-confirm against the step registry.

## Objective

`finalize-step-preference-emitter` runs **after the merge** yet **writes a tracked file**, so its
output can never be pushed through the plan's PR — it lands as an uncommitted diff on main. Either it
runs before the push gate, or its sink is not a tracked source file.

## ⚠ Mechanism — reported by PLAN-40 finalize, re-confirm at D1

- `finalize-step-preference-emitter` is **`order: 80`**; `branch-cleanup` (which merges the PR)
  is **`order: 70`**. So preference-emitter runs **post-merge**.
- It writes `.plan/project-architecture/default/enriched.json` — a **tracked** file (the
  architecture hint promoted from the run's preference pattern).
- `phase-6-finalize/standards/source-edit-pushability.md` requires **source-editing steps to run
  pre-merge** so their edits ride the plan's own PR. A post-merge tracked-file write has **no legal
  path to main** — the executor correctly left it dirty rather than violate a stronger rule.

This recurs on **every** plan whose preference-emitter promotes a hint; PLAN-40 is just where it was
caught and honestly surfaced.

## Deliverables

### D1 — GATE: confirm the order values and classify the sink (mutates nothing)

Re-read the step registry for the real `order` of `preference-emitter` and `branch-cleanup`, and
determine whether `enriched.json` is genuinely tracked (git-tracked, rides PRs) or an artifact that
*should* be `.gitignore`d / declared non-source. The fix branch depends entirely on this:
- if the hint is legitimately **source** → the step must move **before the push/merge gate**;
- if the hint is a **local artifact** → declare its sink non-source (gitignore / non-tracked path)
  so writing it post-merge is legal.

### D2 — apply the chosen fix

Either re-order `preference-emitter` below the source-edit-pushability threshold (`order < 10`, per
the PLAN-40 finalize note) so its write rides the plan PR, **or** relocate/declare its sink
non-source. Do not do both — D1 picks one against the sink classification.

### D3 — the finalize contract detects this class, not just this instance

`source-edit-pushability` should **fail loudly** when *any* step ordered after the merge gate
declares a tracked-file write — a compose-time check that the step graph cannot place a source edit
post-merge. Otherwise the next post-merge source-writing step repeats this silently. (Ties to the
finalize-machinery family, PLAN-36.)

### D4 — regression test

A test asserting no finalize step ordered after `branch-cleanup` writes a tracked path (D3's gate),
plus a test that preference-emitter's output lands committed on the plan branch (D2). Pins the
invariant, not the current order number.

## Expected surface

- the `preference-emitter` step definition (its `order`) and/or its enrich sink path
- `phase-6-finalize/standards/source-edit-pushability.md` (D3 compose-time gate)
- one/two new tests under `test/plan-marshall/phase-6-finalize/**`

**Disjointness:** finalize-step surface — disjoint from `manage-architecture` (PLAN-43), the CI/await
seam (PLAN-42), phase-1-init (PLAN-41), and plan-optimization's running `_markers_search.py`
(PLAN-23) / `manage-execution-manifest.py` (PLAN-35). Emittable now.

## Notes

- The **symptom** (the uncommitted `enriched.json` on main) already landed via **PR #984** — separate
  from this **root-cause** plan. Do not conflate: #984 cleaned main; this plan stops the recurrence.
- Archetype: a step graph that structurally cannot honour its own pushability contract — adjacent to
  the checks-the-wrong-thing / finalize-machinery family (PLAN-36, lesson 16-002).
