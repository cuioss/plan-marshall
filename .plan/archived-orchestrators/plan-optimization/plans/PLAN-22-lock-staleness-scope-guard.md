# PLAN-22: lock-staleness-scope-guard

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Promoted from a LIVE INCIDENT at PLAN-17 #948 (2026-07-20), orchestrator-verified.
> The inverse of PLAN-15 #940: that hardened the auto-reclaim path; this covers the manual-release path.
> Re-ground the exact call sites and store-resolution mechanics at outline.

## Objective

Make "is this lock holder stale?" answerable only from evidence that could actually observe a live
holder. Today the question can be asked from a store view that structurally cannot see the holder, and a
negative answer is treated as proof of death — so a live plan's merge lock can be released by another
session acting in good faith on sound-looking evidence.

## Deliverables

### D1 — staleness inference must query the main-checkout store, never a worktree-scoped view

**Live incident, PLAN-17 #948 (2026-07-20):** the run judged the `steward-provisioning-fail-closed` lock
stale because `manage-status list` and `worktree-list` returned nothing — but both ran with **cwd pinned
to the releasing plan's own worktree**, so they resolved to a **worktree-local store** that could never
have seen the holder. The holder was live in another session and landed as **#950**. No damage occurred
(disjoint files, `no_overlap`, both merged cleanly — orchestrator-confirmed: `e45c7ac8f` and `250f9a4ea`
are both on main), **but the check was unsound and the tooling made the wrong answer the easy one to
reach.** This is the **inverse of PLAN-15 #940**, which hardened `holder_has_live_worktree` on the
*auto-reclaim* path; the *manual release* path has no equivalent guard — `release-under-holder-id` exists,
but the gap is the staleness **inference** that precedes it. **Fix:** resolve the staleness query against
the main-checkout store, and make an unresolvable/worktree-scoped query return **`unknown`, never
`stale`** (fail-closed — the ADR-009 posture PLAN-13 #950 encoded). **Acceptance:** a staleness query
issued from inside a worktree either resolves against the main checkout or returns `unknown`; a release
attempt on `unknown` REFUSES rather than proceeding. Regression test simulating the #948 shape (holder
live in another worktree, query issued from a sibling worktree).

### D2 — sweep CWD-keyed store-resolution call sites for the same class

The root hazard is general: **stores resolved by CWD / git-common-dir silently answer about the wrong
scope.** This is the same class as the known `manage-lessons` cross-repo hazard (removing a remote repo's
lessons through the current repo's store). **Enumerate (do not sample)** the call sites where a store is
resolved by CWD and a *negative/empty* result drives a destructive or authority-bearing decision — lock
release, lesson removal, plan/worktree listing used as an existence proof. **Acceptance:** a written
enumeration with a fix-or-justify disposition per site, in the style of PLAN-13 #950's
`provisioning-fail-closed-audit.md`. Fix the sites where an empty result is read as authoritative.

### D3 — encode the invariant + retire the lesson

Encode "an empty result from a scope that could not have observed the subject is `unknown`, not
`absent`" once — as a guard/helper or structural check — so a new call site cannot regress into it.
Tie to ADR-009 (fail-closed) rather than proposing a new ADR unless outline shows a genuinely distinct
principle. **Acceptance:** a new authority-bearing read that treats an empty CWD-scoped result as proof
is caught structurally, not by incident. Retire the incident lesson rather than leaving it as a watch.

## Out of scope / do NOT expand
- PLAN-15 #940's auto-reclaim `holder_has_live_worktree` predicate — shipped and correct; D1 is the
  MANUAL-release counterpart, not a redo.
- The merge-queue FIFO / `build-queue.json` mechanics and the marshalld build server — different surface,
  plan-server epic.
- Leaf verification (PLAN-20) and the review barrier (PLAN-21) — sibling plans, disjoint surfaces.

## Absorbs
- Open Defect "merge-lock staleness judged from a worktree-scoped store" (PLAN-17 #948 incident) → D1.
- The generalized CWD-keyed store-resolution hazard (incl. the known `manage-lessons` case) → D2/D3.

## Expected Surface
- `manage-locks` / `_locks_core.py` — staleness inference on the release path
- store-scope resolution used by `manage-status list` / `worktree-list` (read-side scope correctness)
- `manage-lessons` store resolution (D2 sweep — fix-or-justify, do not necessarily change)
- a new audit/standards doc for the D2 enumeration; ADR-009 tie-in for D3
- tests: worktree-scoped-query-returns-unknown; release-refuses-on-unknown; #948-shape regression

## Dependencies and Sequencing
- Depends on: none. PLAN-15 #940 (auto-reclaim gate) and PLAN-13 #950 (fail-closed posture + audit-doc
  pattern) are shipped preconditions to build on and mirror.
- Surface-disjoint from PLAN-20 and PLAN-21 (startable in parallel) and from in-flight PLAN-18.

## Size / split guard
3 deliverables — under the ~6 presumption. D2's sweep is the elastic one: if the enumeration proves
large, ship D1 + D3 + the highest-value swept sites and stage the tail as a follow-up, recording the
split as an epic decision (the same shape PLAN-13's split guard used).

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-22-lock-staleness-scope-guard.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-22.md is recorded}
