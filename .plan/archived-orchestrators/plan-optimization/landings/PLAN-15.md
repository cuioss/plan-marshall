# Landing Analysis: PLAN-15 — stale-merge-lock-reclaim

epic: plan-optimization
workstream: WS-07
pr: #940 (squash-merged via queue — commit `ff0c109e7`)

> Verified: `ff0c109e7 fix(manage-locks): auto-reclaim stale merge-lock holders via strengthened
> live-worktree gate (#940)` on main; `_locks_core.py:159` `holder_has_live_worktree` strengthened to
> require a concrete live-worktree marker. Operator narrative corroborated.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Fix stale-holder reclaim | shipped-modified (predicate re-grounded, same intent) | The spec cited `holder_is_dead`; the OUTLINE re-grounded (as the spec instructed) and found that predicate already correct. The real coverage bug was `holder_has_live_worktree` using a bare `worktree_dir.exists()` — an orphaned/empty worktree SHELL masqueraded as mid-recovery and blocked the merge. Fix requires a concrete marker (`.git` gitdir link OR live `.plan/local/plans/{holder}` dir): orphaned shell → auto-reclaim; genuine mid-recovery worktree → protected. Both "distinct stale-holder classes" shared ONE root cause + ONE fix. `merge_lock.py`/`build_queue.py` correct-by-construction (no edit). 4 acceptance tests + 1 contract + 3 repaired fixtures. |

**Spec-fidelity note (positive):** the spec's "re-ground citations at outline" caveat did its job — a
slightly-wrong predicate citation was corrected at outline rather than blindly implemented. Same intent,
correct target.

## Metrics and Anomalies

- 50m43s worked / 3h6m wall / 3.5M tokens.
- Anomalies:
  - **The bug bit its own merge, live** — at branch-cleanup the lock was held by a stale synthetic
    holder `orchestrator-archive-verb` (PLAN-12; no plan dir, no worktree — a harness-killed-archive
    leftover). Running code predated the fix → manual `release-under-holder-id`. Confirms the exact class
    #940 fixes; self-reclaims once propagated.
  - **⚠ Executor leaf UNDER-SCOPED the breaking-change test sweep** — the phase-5 leaf updated the
    contract test + added new tests but missed 3 pre-existing `TestLiveWorktreeGuard` fixtures using
    bare-dir shells; **whole-tree module-tests caught them (3 failures)**, remediated inline. → same
    scoped-vs-whole-tree class **in-flight PLAN-14** targets; also a distinct "leaf must sweep ALL
    pre-existing callers/fixtures of a changed contract, not just add new tests" signal. New watch.
  - Harness killed background builds (known mitigation); both review bots rate-limited (`13-21-001`).

## Routing and Merge Behavior

- CI/merge: green; squash via queue (`ff0c109e7`). Disjoint from in-flight PLAN-14.

## Reconciliation Actions

- [x] status.json PLAN-15 → shipped, pr=940, landing=landings/PLAN-15.md
- [x] epic.md queue row + WS-07 charter → COMPLETE
- [x] Stale-merge-lock watch RESOLVED (fixed by #940; self-reclaims once propagated)
- [x] Watch added: leaf under-scopes breaking-change test sweep (reinforces PLAN-14)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **WS-07 COMPLETE** (single-plan workstream). The stale-merge-lock class that dogged this whole epic
  (~5 incidents across landings) is now fixed at the tool layer — expect it to stop recurring once #940
  is in the running cache.
- **Reinforces in-flight PLAN-14** (scoped→whole-tree): a leaf again passed a scoped check while
  whole-tree caught a real breakage. Feed this datapoint into PLAN-14's outline.
