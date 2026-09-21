# Landing Analysis: PLAN-33 — Session-Binding Store Caller and Conflict Semantics

epic: plan-optimization
workstream: WS-10
pr: #974 (`7d6b8df83`)

> **AUTHORITATIVE.** Written first as provisional (the merge was discovered when
> `git remote prune origin` removed the deleted remote branch and the orchestrator chased the
> signal), then upgraded on narrative arrival.
>
> ✅ **The provisional inference HELD on every point** — 3/3 deliverables, the archive-plan caller
> site, and the non-collision with PLAN-34 all confirmed. Second diff-only landing this session
> (after PLAN-25) whose inference survived the narrative unchanged; consistent with the refined
> rule — the deliverables here were artifact-shaped enough (a caller site, a doctor sweep, a
> rationale note) to read off the diff. **But the narrative added two things a diff cannot show:
> that two spec premises were FALSE, and that the outline found a hazard the spec never carried.**

## Deliverable Evidence vs Spec

Verified against merge commit `7d6b8df83` (8 files, +481/-58). Title: *"chore(platform-runtime):
automate session-store GC and prune orphans"*.

| Deliverable (spec) | File evidence | Inference |
|---|---|---|
| D3 (as executed — caller) — GC caller wired into `default:archive-plan` | shipped | `phase-6-finalize/standards/archive-plan.md` (+59). ✅ **NOT `marshall-steward`** — and the narrative gives the *reason*, which is stronger than the diff: steward was **rejected on merit, not deferred** — it is itself a human-invoked wizard, so it structurally cannot satisfy "runs without a human invoking a doctor verb." PLAN-34 file-ownership was a second, independent block. **A new phase-6 step was also rejected** because PLAN-36 is building a roster-closure regression a 26th step would turn red; `default:archive-plan` was already registered, so no roster row was needed |
| D1 (as executed — orphan-dir sweep) | shipped | `session_binding.py` (+106/-…). The narrative corrects the mechanism: it was **NOT a missing `rmdir`** (that already existed) — the defect was `_iter_slots` only visiting dirs with a *readable slot file*, so 26 dirs survived with 5 slots. The sweep now visits all dirs |
| D2 (as executed — conflict semantics) | shipped as **correct-by-design** | `contract.md` (+8) rationale note + a coexistence regression. **No fail-closed guard was added** — see the false-premise finding below |

**The title-teardown scope (`terminal-title-architecture.md` +91, `_claude_runtime_impl.py` +20)
was legitimate**, as I flagged — `archive-plan` is where a session's binding *and* its title are
torn down, so wiring the GC caller there naturally touches both.

## ⚠ Two false spec premises (both caught at refine) — and a hazard the spec never carried

**This is the most important content of the landing, and none of it is visible in the diff:**

- **D2 premise FALSE — conflicts were never ambiguous.** The spec treated the 88 multiply-bound
  slots as a live correctness question needing a fail-closed-vs-last-driven-wins decision. At
  refine that dissolved: `resolve_plan` is **forward-only**, teardown unbinds **only the caller's
  own slot**, and **no session-close verb exists**. So a multiply-bound plan is not actually
  ambiguous in any reachable path. Shipped as **correct-by-design** with a rationale note and a
  coexistence regression — **no guard added.** My spec's D2 was solving a non-problem.
- **D3 premise FALSE — not a missing `rmdir`.** The spec assumed the GC removed slot files but
  left parent dirs. The `rmdir` already existed; the real defect was `_iter_slots`' visibility
  (readable-slot-only). Right symptom (26 dirs / 5 slots), wrong mechanism.
- **⚠ The OUTLINE found a hazard the spec did not carry — and it drove D1 more than my
  constraint did.** `_plan_is_live` resolves plan dirs **relative to process cwd**. A sweep fired
  from a phase-5 worktree would classify *every other live plan as archived* and **destroy the
  bindings of every concurrently running session.** `archive-plan` runs *after* `branch-cleanup`
  removed the worktree, so cwd is main — which is *why* archive-plan is the correct caller site,
  a reason deeper than "it was already registered." Pinned by a two-residency regression.

**Orchestrator note:** this is the pattern lesson `2026-07-21-22-001` predicts — an
orchestrator-inferred mechanism (here D2's ambiguity and D3's rmdir) falsified at refine. It is
the **fourth consecutive plan** where that happened (PLAN-24/26/29/33). The binding practice is
earning its keep: the spec labelled these as the plan's own hypotheses to verify, and refine did.

## Two tooling defects found (both this epic's territory)

- **`2026-07-22-00-002` — manifest under-reports execution tier.** The manifest stamped
  `verify:coverage` as `per_task` but `architecture resolve` returns `orchestrator` (1221s). The
  leaf only avoided losing a background build because it **defensively re-resolved**. The stamp is
  meant to be *structural enforcement* of leaf-no-background-build; under-reporting silently
  downgrades it to a convention. **New — not owned by any staged plan.**
- **Bound inversion reproduced WITH NUMBERS** (already owned by `2026-07-22-00-001`, the harness
  follow-up PLAN-32 left open): `verify plan-marshall` self-killed at `timeout_used_seconds: 246`
  while the same tree passed **split** (2s + 172s). Every green reported for #974 came from a
  *split* run, never a `verify` run. This is hard evidence the bound-ordering class is still open.

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `974`, landing `landings/PLAN-33.md`)
- [x] epic.md queue row reconciled
- [x] **The GC-caller-in-steward collision risk is CLOSED** — D1 picked `archive-plan`, not steward,
      so no follow-up wiring is owed and PLAN-34 was never at risk from it
- [x] `unrun-GC` pattern: one of the two instances (session store) now has an automatic caller —
      **half the pattern is closed**; the plugin-cache half remains open under PLAN-34
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ NEW — `2026-07-22-00-002` manifest execution-tier under-reporting is UNOWNED.** The manifest
  stamps `verify:coverage` `per_task` while architecture resolves `orchestrator`. The stamp is
  supposed to structurally prevent a leaf from losing a background build; under-reporting reduces
  it to a convention the leaf only survives by re-resolving defensively. **This is a sibling of
  PLAN-20's execution-accounting work** — a candidate follow-up, not staged (queue busy).
- **Bound-ordering class n=3, still open, now with hard numbers** (246s self-kill vs 172s split).
  The harness-side floor follow-up PLAN-32 left owed is confirmed necessary, not theoretical.
- **`_plan_is_live` cwd-relative resolution is a latent trap beyond this plan.** #974 pinned it
  for the archive-plan caller, but any *other* future caller of the session GC (or of
  `_plan_is_live`) from a non-main cwd would re-trigger the destroy-all-bindings hazard. Worth a
  watch: the safety depends on the caller's cwd, which is an implicit precondition, not an
  enforced one.
- **✅ unrun-GC pattern — session half CLOSED.** #974 gives the session GC an automatic caller at
  a *provably-safe* cwd. Only the plugin-cache half (PLAN-34) remains.
- **Landing-record-completeness → n=3** (PLAN-24/25/33), all surfaced by incidental checks. The
  narrative confirms the diff-only inference was fully correct *this* time — but it also proves
  the diff would have **silently missed the two false premises and the cwd hazard**, which are the
  most valuable findings. The hand-off, not the check, is the gap.
