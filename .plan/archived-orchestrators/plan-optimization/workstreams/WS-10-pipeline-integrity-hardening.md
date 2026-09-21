# WS-10: Pipeline Integrity Hardening

epic: plan-optimization

> Charter document for one workstream. Tracked in the epic `status.json` `workstreams[]` field.

## Charter

Close the **survivor set** — the plan-worthy defects this epic's own landings surfaced but did not fix.
All three share one root theme: **the pipeline reports a state it has not earned.** A leaf reports a
task verified while never running the tests that task could break; finalize records a step under a key
that does not match the manifest, so its own bookkeeping cannot find it; a lock-holder is judged dead
from a store view that could never have seen it alive; and the review barrier files bot rate-limit
notices as actionable findings while its completeness guard loops back on triage that has not run yet.

This is the same family as PLAN-01 #914 ("code local but pipeline acts shipped") and PLAN-02 #927
("green when CI disagrees") — but at the *accounting and concurrency* layer rather than the commit layer.
Closes when each survivor is fixed at the tool layer with a regression test, and its lesson retired
rather than re-observed.

> **Thematic note for the epic-close decision:** this workstream is NOT token-usage optimization — the
> epic's original Vision. These are correctness byproducts that accumulated across Wave 2. Staged here
> for ledger continuity (all the recurrence history lives in this epic's Watches). If the operator
> prefers a clean boundary, WS-10 is the natural seed for a successor epic and can be migrated intact.

## Scope

- In scope: phase-5 leaf per-task verification scope; finalize step-record key resolution; `manage-locks`
  staleness inference and its store-scope resolution; the automatic-review noise pre-filter and
  completeness-guard ordering.
- Out of scope: re-fixing anything already shipped (PLAN-10 #936's CodeRabbit-specific filter, PLAN-15
  #940's auto-reclaim gate, PLAN-14 #942's whole-tree finalize gate) — each of these plans is the
  *residual* of one of those, not a redo. The marshalld build-server test-isolation facet belongs to the
  plan-server epic, not here.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-20-execution-accounting-integrity | staged | Leaf runs the tests it can break (22-001, n=3) + finalize step-record key matches manifest `step_id` (12-003, n=5) |
| PLAN-21-review-barrier-residuals | staged | Bot-agnostic rate-limit classifier (13-21-001) + completeness-guard vs unified-triage ordering (05-001) + gemini sunset pruned project-wide |
| PLAN-22-lock-staleness-scope-guard | staged | Staleness must query the main-checkout store, never a worktree-scoped view (#948 incident) + CWD-keyed store-resolution sweep |

## Sequencing and Surface Notes

- **All three are mutually surface-disjoint and startable in parallel NOW** — this grouping was chosen
  precisely to achieve that:
  - PLAN-20 → phase-5 leaf verification composition + finalize step-record/manifest `step_id`
  - PLAN-21 → `github_pr.py` / `github_re_review.py` / `_ci_barrier.py` / automatic-review step
  - PLAN-22 → `manage-locks` / `_locks_core.py` + store-scope resolution
- **Why not one plan:** the combined set is ~8 deliverables — well past the ~6 split presumption.
- **Why not four:** splitting PLAN-20's two halves into separate plans puts both on the
  execution-manifest surface, creating an adjacency that would force sequencing and cost the parallelism.
  Keeping them in one plan is what makes the other two safely concurrent.
- Adjacent to **PLAN-18** (in flight, WS-09) only weakly: PLAN-21 touches the review barrier while
  PLAN-18 touches steward/ci provisioning — disjoint. PLAN-22 touches `manage-locks`, which PLAN-18 does
  not. No sequencing constraint against PLAN-18.
