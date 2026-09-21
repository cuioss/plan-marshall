# WS-06: Derived Epic Sets

epic: test-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-06-derived-epic-sets.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The epic holds three cross-file sets in prose — **the partition** (which plan owns which test
directory), **the collision matrix** (which plans may not run concurrently), and **the per-slice
attribution** (how the budget count distributes across slices) — with nothing deriving them and nothing
checking them. Nine independent verification rounds found a defect of exactly this class in every one
of the nine, and three successive structural remedies each failed; the last two contradicted themselves
**inside the commit that added them**. This workstream computes the three sets from the sources that
define them and makes a drifted document a red build rather than a finding a later round may or may not
make.

## Scope

- In scope: a checker that parses the epic's plan documents into a three-class model (declarative /
  derived / prose), derives the three sets, compares each against what the documents assert, and gates
  on **new** disagreement while baselining what already exists; its tests under `test/`; and the one
  partition row registering that test location.
- Out of scope: **editing the epic's plan documents to resolve a disagreement the check finds** — a run
  that writes the checker and edits what it checks can make the check pass by moving either side, and
  no independent verdict is left. Also out: generalising the checker beyond this epic; any `test/`
  refactoring; changing the doctor's rules or output format (WS-03's — a shape that makes the
  derivation impossible is **recorded** for it).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-120-derive-the-epics-cross-file-sets | staged | Four deliverables, D1 gating. Land it earliest of what is left — it checks the documents every other plan is executed from |

## Sequencing and Surface Notes

- **`120` should land earliest of what remains.** It checks the documents every other plan is executed
  from, and nine verification rounds established that nothing else does. Its value is highest before
  the remaining plans run against those documents, not after.
- **Its one collision is conditional and it says so.** `pm-plugin-development:plugin-script-architecture`
  may place its checker under `marketplace/bundles/**`, which is WS-03's exclusive tree; if the standard
  admits a non-bundle location the collision is inert and the run reports that it was.
- **The baseline is not the hand-maintained artifact this plan abolishes.** Every entry is re-derived
  from the sources on every run; the baseline only decides whether an already-derived disagreement fails
  the build or warns, and a hand-edited entry the derivation does not reproduce is reported as stale.
- ⛔ **The ingestion into this orchestrator ledger changes `120`'s premise and its surface.** The plan
  was written against `doc/plans/test-quality/`, which no longer exists — its documents are now this
  epic's `archive/` tree and its `plans/` specs. `120`'s spec carries the re-scoping; the deliverables'
  substance is unchanged, but the paths it parses and the gate it wires into are not the ones the
  original names.
