# Landing Analysis: PLAN-115 — A plan-less PR can be opened but never corrected

epic: truthful-signals
workstream: WS-01
pr: 1065 — merged; `origin/main` at `468b8227`

## Ground-truth corroboration

- ✅ **PR #1065 merged.** ⚠ Recorded as an explicit reconciliation lesson: **earlier today this plan's own
  landing message claimed "PR: #1065" under a *"What landed"* heading while `ci pr view --head` returned
  `state: open`, `merge_state: unstable`, `review_decision: none`.** The row was correctly held at
  `launched` then and is transitioned only now, on the merge. **Four instances of the pre-merge-landing
  archetype; owned as `review-apparatus`'s PLAN-PR-010.**
- ✅ Finalize 21/21, `archive-plan` completed, worktree removed, working tree clean.

## ⚖ THE SEMANTIC MERGE — ORCHESTRATOR-VERIFIED SOUND, no defect found

The operator flagged a cross-PR semantic merge in `_resolve_footprint` and asked for a sanity-check. The
rebase hit a real content conflict against upstream **#1066**: #1066 split `None` (unresolvable) from `[]`
(resolvable-but-empty); this plan migrated to `resolve_plan_context` but returned `[]` for the unresolvable
case. The operator merged **this plan's resolver mechanism with #1066's `None` contract**.

**Verified at HEAD by symbol, four axes, all pass:**

1. OBSERVED — signature is `_resolve_footprint(plan_id: str) -> list[str] | None`, and there are **three
   distinct return-`None` paths**: `not context.has_worktree`, `except WorktreeResolutionError`, and
   `not worktree.is_dir()`. **#1066's contract is preserved, not merely type-annotated.**
2. OBSERVED — `resolve_plan_context(plan_id, ensure=False)` is the resolution seam. **This plan's mechanism
   is the one in use**, and `ensure=False` is the correct mode: documented as *"a pure path computation —
   no existence check, no side effects."*
3. OBSERVED — `[]` is reserved for the resolvable-and-genuinely-empty case, per the docstring.
4. ⭐ OBSERVED — **the merge pre-empted an EMERGENT hazard neither PR carried alone.** The docstring names
   it: *"the resolver's `worktree_path` falls back to the main checkout for a plan that is not
   worktree-bound, so gating on the path would start deriving a main-checkout footprint instead of
   reporting the unresolvable state."* Gating on `has_worktree` rather than path truthiness neutralizes it.
   ⛔ **This is the same wrong-tree failure mode the operator hit separately in this run** — passing the
   main checkout as `--worktree-path` to a CI precondition and getting a green that was `main`'s HEAD. Here
   the merge closed it *before* it could produce a footprint from the wrong tree.

⭐ **The `try` placement is correct in a non-obvious way, and worth recording because the naive version
looks safer while being worse.** `resolve_plan_context` sits OUTSIDE the `try` because under `ensure=False`
it cannot raise `WorktreeResolutionError`; `context.has_worktree` sits INSIDE because `PlanContext`'s three
worktree faces are **lazy properties** (they shell out to `manage-status get-worktree-path` on first
access) and `worktree_path` documents `Raises: WorktreeResolutionError`. ⇒ Had the lazy access been placed
outside, the guard would be **vacuous and the exception would escape**; had the resolver call been wrapped
inside, the guard would look broader while catching nothing extra.

⛔ **The operator's residual concern STANDS and is the actionable residue: no test pins the real function's
return — every test monkeypatches it.** So the merged contract is **correct by inspection but unprotected
against regression**. ⇒ Owed: a test exercising the real `_resolve_footprint` across all three states
(unresolvable → `None`, resolvable-empty → `[]`, resolvable-nonempty → paths). ⚠ This is the
*monkeypatched-tests-cannot-see-a-contract-change* shape — the same family as the shipped PLAN-54
(retrospective-checker assertion integrity).

## Deliverable Fidelity

7/7 as claimed. ⭐ **D1's population derivation is again the load-bearing outcome** — the request was framed
as a two-verb `ci` asymmetry; the derived population was **~18 incidental consumers across 11 skills**,
each re-deriving a working tree from a plan id it did not need. ⭐ **D4 ABSORBED rather than mirrored**: the
pre-existing `ci pr create --body-file` outlier was removed so exactly one shape exists — a retirement, not
a second convention. **D6 shipped a population-derived straggler guard** (`_analyze_plan_path_in_scripts.py`
with a Form C resolver-bypass detector), so a straggler cannot silently reappear.

## ⛔ THE AUDITING TOOLS REPRODUCE THIS EPIC'S THEME — two defects, both ours

1. ⛔ **`affected_files_recall` is DEAD BY CONSTRUCTION for every worktree-backed plan.** It reported a
   confident **"Recall 0%"** where real recall is **~89%**, because `branch-cleanup` (step 15) **removes the
   worktree before `plan-retrospective` (step 16) reads it**. ⭐ **An ordering defect wearing a measurement
   result's clothes** — and "0%" is the most damaging possible rendering of "cannot measure", because it is
   a plausible value that invites action. ⚠ **This is the PLAN-10 archetype exactly**: a finalize-time
   component whose own finalize ordering prevents it from working. Same family, new instance.
2. ⛔ **`direct-gh-glab-usage` returned a vacuous `total: 0` under its own canonical invocation** — a
   detector reporting a clean sweep it never performed. **Vacuous-guard family, n=8.**

⇒ Both stay in this epic (precedent: PLAN-51 retrospective-compile-report-silent-omit and PLAN-54
retrospective-checker-assertion-integrity both shipped here). Filed as Open Defects.

## Reconciliation Actions

- [x] row `status` → `shipped`; `landing`; `plan_marshall_plan_id` stamped (`pr` = 1065 was stamped earlier
      while the row was correctly still `launched`)
- [ ] 13 candidate-lesson messages (7 lessons-capture + 6 retrospective) — pending disposition; **its
      finalize is now quiet, so they are drainable**
- [ ] post-merge PR revisit for #1065 — owed (ours: `tools-integration-ci`)
- [ ] a test pinning the real `_resolve_footprint` return across its three states

## Parallelization Consequence

PLAN-115 held `tools-integration-ci`. Its landing **clears that surface**, so **PLAN-TRUTH-004** loses its
blocker — re-derive from the spec at emit, not from this sentence. Round-3 #5 (by-commit lookup) and
round-4 #6 (post-merge boundary) also land there and must be sequenced against each other.
