> ⛔⛔ **SUPERSEDED 2026-08-08 — ABSORBED INTO `PLAN-TRUTH-054`.**
> Both plans targeted `_cmd_baseline_reconcile.py`'s `auto_reconciled: true` path with **opposite
> remedies** (this plan: the probe never mutates; 054: the mutation fails closed). The collision was
> invisible from inside either spec because neither named the other's remedy. **This plan's remedy
> WON** and is carried into 054 as D2′/D3′ — see 054 § "ABSORBS PLAN-TRUTH-006".
> **Do not implement this spec. Do not emit it.** It is retained as the record of what was absorbed
> and why, per *close freezes, never deletes*.

# PLAN-TRUTH-006: `baseline-reconcile --no-emit` Persists a Merge Commit Despite Its No-Mutation Contract

> Renamed from **PLAN-52** on 2026-07-30 (see `plan-id-rename-map.md`). ✅ Its "blocked while PLAN-92
> runs" gate is DISCHARGED — PLAN-92 shipped as #1041.

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced by PLAN-35's (#985) finalize — lesson `2026-07-22-21-001`, caught
> **incidentally** in a `git worktree list` run. Grounded @ `287c3c86d`. This is a probe that claims
> "no mutation" while mutating — doc-contract-divergence with a **silent, dangerous** effect.

## Objective

`baseline-reconcile --no-emit` is the finalize sync-baseline classifier probe. Its contract
(`finalize-step-sync-baseline.md:72`) is explicit: it "performs only `fetch + diff + merge-tree` and
**never mutates the working tree**." But on the `auto_reconciled: true` path it **leaves a merge
commit as the feature-branch HEAD**. Unnoticed, a downstream step **force-pushes that merge commit
into a squash-merge repo, unverified** — the exact silent corruption the probe's read-only contract
exists to prevent. Restore the invariant: the probe mutates nothing, on every path.

## ⚠ Mechanism — verified at `287c3c86d`

- **Contract (verified):** `finalize-step-sync-baseline.md:72` — "The probe performs only `fetch +
  diff + merge-tree` and never mutates the working tree." `:26` — the step "performs **NO
  force-push**"; the branch is not even pushed yet at `order: 3`.
- **Defect (lesson `2026-07-22-21-001`):** on the `auto_reconciled: true` classification path, the
  `--no-emit` probe left a **merge commit as feature-branch HEAD** — a persisted working-tree/branch
  mutation the contract says cannot happen. `merge-tree` is inherently non-mutating, so something on
  the auto-reconcile path performs a **real merge** instead.
- **Blast radius:** the finalize flow trusts the branch HEAD; a persisted merge commit would ride the
  later `push` / `branch-cleanup` force-push into a **squash-merge** repo, unverified.

## Deliverables

### D1 — GATE: locate the merge-commit-persisting path (mutates nothing)

Find the `baseline-reconcile` implementation (the `git-workflow` verb the standard reuses) and the
`auto_reconciled: true` code path. Identify exactly where it creates/persists a merge commit instead
of staying on `merge-tree` (a real `git merge` vs the non-mutating `git merge-tree`). Confirm the
contract text (`:72`) it violates and that the defect is confined to `auto_reconciled: true`.

### D2 — the probe is non-mutating on every path

Make `--no-emit` leave the feature-branch HEAD **unchanged** on all classifications. If the
auto-reconcile classification needs a trial merge, perform it via `git merge-tree` (non-mutating) or
in a discarded detached/scratch state — never a real merge that moves the branch ref. The probe
classifies; it does not reconcile.

### D3 — fail-loud guards on both sides

(a) A post-probe assertion that the branch HEAD is **byte-identical** before/after the probe — if the
probe moved it, error loudly rather than proceed. (b) The downstream `push` / `branch-cleanup`
force-push must verify HEAD is the expected non-merge commit before pushing into a squash-merge repo
(a merge commit at push time is a hard stop, not a silent force-push).

### D4 — regression test

Drive `baseline-reconcile --no-emit` on an `auto_reconciled: true` scenario and assert the
feature-branch HEAD is unchanged (no merge commit persisted). Pin the no-mutation contract on the
exact path that broke it.

## Expected surface

- the `git-workflow` `baseline-reconcile` implementation (the `auto_reconciled` merge path)
- `phase-6-finalize/standards/finalize-step-sync-baseline.md` (if the contract needs a guard clause)
- possibly `phase-6-finalize` push / branch-cleanup (D3 push-time HEAD check)
- a test under `test/plan-marshall/**` covering the probe's no-mutation invariant

**Disjointness:** `git-workflow` baseline-reconcile + finalize sync-baseline. Adjacency: `phase-6-finalize`
is also touched by PLAN-44 (source-edit-pushability, different file) and PLAN-50 (finalize-step lane
overrides, different files) — coordinate at outline. Disjoint from PLAN-41/42/43/46/45/47/48/51/27.

## Notes

- Archetype: **doc-contract-divergence + silent-mutation** — a probe documented as read-only that
  persists a branch mutation. Confident-signal-adjacent: the caller trusts "no mutation" and force-
  pushes on that trust. Sits in the epic's truthful-machinery theme.
- Severity: higher than a cosmetic contract gap — the unnoticed path force-pushes an unverified merge
  commit into a squash-merge repo. D3's push-time guard is the safety backstop even if D2 regresses.

## `prune-local-and-remote-ref` hard-errors on the NORMAL path

`prune-local-and-remote-ref` **hard-errors when the local branch is already gone** — which is the
**steady state of the worktree flow**. So **every worktree-based finalize hits an error path the
documentation says degrades gracefully.**

⛔ **Not an edge case: it is the normal path for any worktree-isolated plan**, which is the default
shape here. The reporter rated it the higher-value of their two finalize findings and that holds — a
documented graceful-degradation that hard-errors on the common path trains operators to ignore
finalize errors, which is how the *next* real one gets missed.

⚠ D1 must decide whether the behaviour or the documentation is wrong, and fix that. **Do not simply
make the error quieter** — a suppressed error on the normal path is strictly worse than the current
loud one.

## Lessons Carried (bound 2026-07-25 · lessons-triage)

The plan lifecycle MUST carry the lesson below so it lives/moves with the plan and leaves the global
corpus when the fix lands: at phase-1-init run
`manage-lessons convert-to-plan --lesson-id {id} --plan-id {plan_marshall_plan_id}`; the finalize
`lessons-housekeeping` step then retires it (provenance to the tombstone `--reason`).

- `2026-07-22-21-001` — baseline-reconcile `--no-emit` leaves a merge commit on the feature branch
  instead of aborting its probe; the exact defect this plan closes.
