# Landing Analysis: PLAN-34 — Steward Owns the Plugin-Cache Lifecycle

epic: plan-optimization
workstream: WS-10
pr: #976 (`a870157ab`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `a870157ab` (20 files, +1970/-78). **4/4 shipped.**

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — fail-closed cache-freshness gate + consumer Stage-1 wiring | shipped | `cache_freshness.py` (+235, NEW), `upgrade.py` (+29), `test_cache_freshness.py` (+277) |
| D2 — union-keep retention sweep + `system.retention` knobs | shipped | `cache_retention.py` (+399, NEW), `manage-config/data-model.md` (+12), `test_cache_retention*.py` (+480 across two files) |
| D3 — marker-saturation repair at source | shipped | `generate_executor.py` (+128), `marketplace_bundles.py` (+23), `test_preflight_pollution.py` (+98), `test_marketplace_bundles.py` |
| D4 — `upgrade-flow.md` docs + meta/consumer asymmetry | shipped | `upgrade-flow.md` (+153), `SKILL.md` (+17) |

## ⚠⚠ CORRECTION TO THE ORCHESTRATOR'S SESSION-LONG FRAMING

**I repeatedly stated this session that "the plugin-cache 7-day GC exists, is documented, works
when invoked, and has simply never run" — and grouped it with the session-binding GC under one
`unrun-GC pattern (n=2)`. The D1 gate proves that framing WRONG.** The two halves are different
defects, and I conflated them:

| | Session store (PLAN-33 #974) | Plugin cache (PLAN-34 #976) |
|---|---|---|
| GC logic | **Exists and works** (`session doctor --fix`) | **Does not exist** — no `unlink` anywhere |
| The "7-day GC" | real | **documented FICTION** — 3 `.orphaned_at` write sites, **zero delete** |
| Missing piece | a **caller** | the entire **reaper** |

So my repeated "there is a delete-time oracle to read before pruning" (PLAN-33/34 specs) was based
on a mechanism that **does not exist**. PLAN-34's D1 verify-first gate is exactly what caught it —
had the plan trusted my framing, it would have looked for a delete oracle that isn't there.

## The D1 gate falsified BOTH premises — but UPWARD, not downward

The previous three falsified-premise plans (PLAN-24/26/29) shrank or re-scoped when the premise
broke. **PLAN-34 is the first where falsification made the plan LARGER:**

- **(a) Preflight cannot detect cache-version skew — structurally.** Every input it reads is local
  (`dist-manifest.json` via a cache-first `base_path`), so it answers *"is my executor consistent
  with my cache?"* — never *"is my cache current?"* Half 1 did **not** shrink to docs (my spec
  offered that as the shrink path); the fail-closed freshness gate was genuinely needed.
- **(b) No delete-time oracle because there is no unlink at all.** Disk probe: **580/580 version
  dirs marked, 0 live, newest included.** The fiction had **already silently disabled two live
  mechanisms** — `_detect_multi_version_pollution` was vacuous, and `find_bundles` was stuck in a
  degraded Tier-3 fallback. **That is where D4 came from** — the marker saturation wasn't cosmetic
  disk growth, it had broken real machinery.

**This closes the plugin-cache half of what I'd called the unrun-GC pattern** — correctly reframed
as "no reaper existed; steward now owns fetch + prune with a union-keep retention and the
live-version pin." Both halves of the (now properly-understood) two-defect pair are shipped.

## Metrics and Anomalies

- Tokens: **2.5M** · Duration: **2h38m**
- Deploy: 1112 files, **0.1.1187**; executor regenerated
- ⚠ The dev cache still shows **63 `plan-marshall` markers** unpruned — expected: the retention
  sweep runs *during* `marshall-steward upgrade`, which is owed. The fix shipped; the cleanup
  happens on the next steward run, not at merge.

## Routing and Merge Behavior

- **Review**: **0 comments, nothing to compare** — every catch was local (the D1 gate, self-review
  93 candidates). Continues the epic pattern.
- **CI/merge**: all green, merged via queue, worktree removed, `main` then advanced to `a870157ab`
  (and since to `1cfa37044` via cross-epic #977 — see Follow-Ups).
- **Surface collisions**: none. The steward + `generate_executor.py` + `marketplace_bundles.py`
  footprint stayed clear of the concurrent PLAN-37 (manage-providers) and PLAN-39
  (manage-execution-manifest). The PLAN-33 non-collision I flagged held: PLAN-33 wired its GC
  caller into `archive-plan`, never steward, so PLAN-34 owned steward uncontested.

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `976`, landing `landings/PLAN-34.md`)
- [x] epic.md queue row reconciled
- [x] **`unrun-GC pattern` watch RETIRED and CORRECTED** — reframed as a two-defect pair, both now
      shipped (session-store caller #974; plugin-cache reaper #976). The "n=2 pattern" label was my
      conflation; recorded as such.
- [x] New watch: **scope_creep_check structurally inert** (see Follow-Ups) — the vacuous-guard family
- [x] Cross-epic #977 (test-suite PLAN-03) noted landed
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ NEW — `scope_creep_check` is structurally inert.** It reports `reason: no_baseline_sha` on
  **every** call because `references.json` carries no `plan_creation_sha`. **A guard reporting
  clean while doing nothing** — precisely the vacuous-gate family this plan just fixed (the
  saturated marker that made `_detect_multi_version_pollution` vacuous), and the same class as
  PLAN-23's marker-detector (`search-markers` matches nothing) and the roster-count PLAN-36 fixed.
  **This is now a repeated defect archetype worth a dedicated sweep**: *guards that pass because
  their predicate never fires.* Candidate plan — not staged (three running).
- **The steward provisioning-stamp lag is now self-healing on the next upgrade** — #976's freshness
  gate + retention run *during* upgrade, so the owed `/marshall-steward` will both reconcile the
  stamp AND prune the 63-marker cache in one pass. The debt and the cleanup converge.
- **Cross-epic: #977 landed** (test-suite-quality PLAN-03, `propagate-parallel-plan-hardening`) —
  parallel-plan test isolation + time-bomb test hardening. That epic is progressing; its PLAN-02
  #966 still needs an `analyze slug=test-suite-quality` in its own ledger.
