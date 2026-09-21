# PLAN-TRUTH-054: `baseline-reconcile` anchors on a stale phase-1 SHA, gives mutually inconsistent verdicts, and one of them auto-merges

epic: truthful-signals
workstream: WS-01

## Objective

`baseline-reconcile` decides whether a branch has diverged from `origin/main` and, on one verdict,
**merges automatically**. It anchors every range on a SHA captured at **phase-1-init**, which cannot
describe divergence at phase-6.

## OBSERVED — first-party during PLAN-TRUTH-035 / PR #1083, and it fired TWICE with TWO answers

| Call site | Verdict |
|---|---|
| `sync-baseline` | `classification: no_overlap` |
| `branch-cleanup` | `classification: overlap_no_content_conflict`, **"2 upstream commits"** |

**Ground truth at both moments: the branch was 0 commits behind `origin/main`.**

⇒ ⭐ **The two answers are not merely different — they are mutually inconsistent, and NEITHER matches
reality.** A detector that returns two contradictory verdicts about one state in one run has no
defensible reading; there is no way to consume it correctly.

## Root cause — verified by code read, not inferred from the symptom

`workflow-integration-git/scripts/_cmd_baseline_reconcile.py`

- **`_resolve_baseline_sha()` (:119)** documents its own preference order as *"`status.metadata.worktree_sha`
  (captured at phase-1-init) → current worktree HEAD"* and returns the **phase-1-init SHA**.
  ⛔ **It never computes a merge-base.**
- **`_list_upstream_commits()` (:246)** runs `git log {baseline_sha}..origin/{base_branch}`.
- **`_list_in_flight_files()` (:555)** runs `git diff --name-only {baseline_sha}..HEAD`.

⇒ `{worktree_sha}..origin/main` is **not** *"commits I am behind by"*. It is *"commits reachable from
`origin/main` but not from the SHA this plan started at."* Those sets diverge the moment the branch's own
history advances past that anchor.

⭐⭐ **And the script CAUSES that divergence itself.** Its focused-reconcile path (**:415**) runs
`git merge origin/{base_branch} --no-edit`. After that merge the merged-in upstream commits are in the
branch's history **yet are still not ancestors of `worktree_sha`** — so the next call re-reports them as
upstream. **That is the "2 upstream commits" over-report, and it is self-inflicted.**

The same stale anchor inflates the in-flight set: `{worktree_sha}..HEAD` after a merge includes the
upstream files, so `upstream_files & in_flight_files` becomes non-empty **for files the plan never
touched**, and `overlap` goes spuriously true.

⇒ **The correct anchor is `git merge-base HEAD origin/{base_branch}`, recomputed per call.**
**A SHA captured once at phase-1-init cannot describe divergence at phase-6.**

## ⛔⛔ Why this outranks an ordinary reporting defect: one verdict MUTATES

`overlap_no_content_conflict` routes to the focused-reconcile path, which **runs `git merge`
automatically**. ⇒ **A verdict derived from a stale anchor triggers an unrequested merge**, and that
merge then makes the *next* call's anchor worse. ⭐ **A wrong read that also writes is a different
severity class from a wrong read** — and this one is self-amplifying.

⚠ **`no_overlap` is the benign-looking half and is equally unreliable** — it was returned in the same
run against the same state. **A remedy that only fixes the merging path leaves a false-clean verdict
live.**

## ⭐⭐ ABSORBS `PLAN-TRUTH-006` (2026-08-08) — and resolves a CONTRADICTION between them

`PLAN-TRUTH-006` (*baseline-reconcile persists a merge commit*) is **superseded and absorbed here**.
Both plans targeted `_cmd_baseline_reconcile.py`'s `auto_reconciled: true` path, and they did not
merely overlap — **they prescribed opposite remedies for the same code path**:

| Plan | Remedy for the auto-merge verdict |
|------|-----------------------------------|
| `-006` D2 | The probe **never mutates**. `--no-emit` leaves the branch HEAD unchanged on every classification; a trial merge uses `git merge-tree` or a discarded detached state. *The probe classifies; it does not reconcile.* |
| `-054` D2 (original) | The mutation **stays but fails closed** — derived from a freshly computed range, or it declines to classify. |

⛔ **Whichever landed second would have deleted or hollowed the first.** 006-first leaves 054's D2
with no auto-merge to harden; 054-first hardens a mutation 006 exists to remove. Neither spec named
the other's remedy, so the collision was invisible from inside either one.

**RESOLUTION — 006's remedy WINS and replaces this plan's D2.** A classifier probe whose contract
(`finalize-step-sync-baseline.md:72`) says it *"performs no writes"* must not move a branch ref;
hardening the write keeps a documented-contract violation alive in a softer form. ⇒ **D2 below is
superseded by D2′:**

- **D2′ — the probe is non-mutating on every path.** `--no-emit` leaves the feature-branch HEAD
  unchanged on **all** classifications, including `auto_reconciled: true`. A trial merge is performed
  with `git merge-tree` or in a discarded detached state — never a real merge that moves the ref.
- **D3′ — fail-loud guards on both sides** (from 006 D3): a post-probe assertion that HEAD is
  unchanged, so a regression is caught at the probe rather than discovered at the landing.

⭐ **What 054 keeps that 006 never addressed**: the **stale phase-1 anchor** (D0/D1). 006 assumed the
range was right and only the mutation wrong. Both halves are needed — an anchor recomputed per call
AND a probe that does not write. That is why this is an absorption rather than a swap.

⚠ **Scope check after absorption**: this plan now carries D0, D1, D2′, D3′ plus its original tail.
Re-count at outline against the ~6 split guard; if it exceeds it, split along the
**anchor** / **mutation** seam, which is the natural boundary and was the original plan boundary.

## Deliverables

1. **D0 — GATE: derive every consumer of the baseline SHA and every verdict's side effects.** ⛔ **Both
   directions**: sites that READ the anchor, and sites that MUTATE on a verdict. ⚠ **`worktree_sha` is
   also the field `PLAN-TRUTH-046` found recording the wrong tree** — check whether this consumer
   inherits that defect too, or is independent of it. **Two plans reading one field is how a fix in one
   silently changes the other.**
2. **D1 — anchor on `git merge-base HEAD origin/{base_branch}`, recomputed per call.** ⭐ **Load-bearing.**
   ⛔ **Per call, not cached** — a cached merge-base re-creates the defect with a shorter staleness
   window, which is harder to observe rather than fixed.
3. **D2 — make the auto-merge verdict fail closed.** A classification that triggers a mutation must be
   derived from a freshly computed range or **decline to classify**. ⚠ **Confirm no flow depends on the
   automatic merge happening unconditionally** before changing it — if one does, make it explicit.
4. **D3 — the two verdicts must be reconcilable.** Two calls in one run against one unchanged state must
   not produce contradictory classifications. ⛔ **A test that pins this is the deliverable**, not a
   caveat in a doc.
5. **D4 — tests, each verified to FAIL pre-fix.** (a) **The live fixture**: a branch 0 commits behind,
   after a focused reconcile, reports `no_overlap`/0 upstream at BOTH call sites. (b) The in-flight set
   excludes files the plan never touched. (c) The merge-base is recomputed, not read from status. (d) A
   contradictory verdict pair across two calls fails.

## Claim Labels

- **OBSERVED (plan-reported, first-party, verified by CODE READ rather than inferred from the symptom —
  the filer says so explicitly)**: both classifications, the "2 upstream commits" figure, the 0-behind
  ground truth, and the four line references (`:119`, `:246`, `:415`, `:555`).
- ⚠ **NOT independently re-derived by this orchestrator.** ⭐ The line references are cheap to check and
  the file is small — **re-read all four at D0.** *A corrective is a hypothesis until the named site is
  read.*
- **HYPOTHESIS**: the self-inflicted-divergence mechanism (the `:415` merge making the next call's
  anchor wrong) is the complete explanation for the "2 upstream commits". ⭐ Strong — it predicts exactly
  the observed number and direction — **but it was reasoned from the code, not instrumented.** Confirm
  by reproducing.
- ⛔ **NOT ESTABLISHED**: how often the auto-merge has fired on a stale verdict historically. **This has
  been live for an unknown number of plans.** D0 should say whether the blast radius is knowable at all.

## Expected Surface

- **OBSERVED**: `workflow-integration-git/scripts/_cmd_baseline_reconcile.py`
- **HYPOTHESIS**: `phase-6-finalize` `sync-baseline` / `branch-cleanup` step docs — the two call sites
- **HYPOTHESIS**: `manage-status` — `status.metadata.worktree_sha`, shared with `PLAN-TRUTH-046`

## Dependencies and Sequencing

- ⚠ **Shares `status.metadata.worktree_sha` with `PLAN-TRUTH-046`** (which found `main_sha` recording
  the worktree HEAD). ⛔ **SERIALIZE — and whichever runs second must re-ground**, because the first may
  change what that field means.
- ⚠ Adjacent to `PLAN-TRUTH-006` (baseline-reconcile persists a merge commit) — **same script, and it may
  already own part of D1.** ⛔ **Evaluate absorption at outline** — this is the second defect filed
  against that file.
- ✅ Disjoint from `PLAN-TRUTH-047` (running: `ref-code-quality` + lessons corpus).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-054-baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges.md"
```

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -058

**Component:** `workflow-integration-git (branch-state verdicts that mutate)` · **Deliverables after merge: 9** (raised cap is 12).

Both plans are verdicts computed by `workflow-integration-git` that **trigger a mutation on a
classification derived from the wrong state**.

- **`-054`** — `baseline-reconcile` anchors every range on a stale phase-1 SHA, and one verdict
  auto-merges. ✅ **CONFIRMED at HEAD: `_cmd_baseline_reconcile.py` contains ZERO `merge-base`
  occurrences**, so the anchor is not recomputed per call.
- **`-058`** — `no_remote` conflates *never-pushed* with *merged-and-deleted*, and the documented remedy
  **resurrects a merged branch**. ⭐ The contract was saved only by an agent **declining to obey it**.

⭐ **Same shape, same module, opposite ends of one decision**: 054 is *the range is wrong so the verdict
is wrong*; 058 is *the verdict is right but its two causes need opposite remedies*. Both end in a
destructive git action taken on an under-determined classification.

⚠ **This plan already absorbed `-006`** (the probe mutating despite a no-write contract). With `-058` it
now owns the whole `baseline-reconcile` / `branch-sync-state` decision surface — which is exactly the
component grouping that makes it parallel-safe against everything else.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count at outline; overlapping deliverables COLLAPSE rather than concatenate.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
