# Landing Analysis: PLAN-36 — Finalize Machinery Integrity

epic: plan-optimization
workstream: WS-10
pr: #973 (`6a6312db0`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## The headline: the binding practice worked exactly as designed

PLAN-36 was the **first spec written under lesson `2026-07-21-22-001`** — every mechanism
labelled OBSERVED or HYPOTHESIS with a named confirm/refute artifact. The narrative reports that
**every named artifact was read before implementing**, and the three verdicts came back:

| Deliverable | Staged label | Verdict at execution |
|---|---|---|
| D1 — bundle derivation | **OBSERVED** | **CONFIRMED** — phantom `marketplace` bundle real and reachable (26 files) |
| D2 — dispatch roster | **HYPOTHESIS** (~5-step shortfall) | **CONFIRMED but LARGER** — 25 registry steps vs the roster's claimed 17, not a 5-step gap |
| D3 — completion guard | **HYPOTHESIS** (evadable guard) | **REFUTED** — the guard already existed and fired correctly; re-scoped |

**This is the practice's whole purpose realized in one plan**: one hypothesis confirmed as-stated,
one confirmed-but-underestimated, one refuted-and-re-scoped — and *no code was written against an
unverified mechanism*. Had D3 been asserted as fact (the pre-practice default), an **eighth
point-fix would have shipped for a guard that already works.** It did not.

## Deliverable Fidelity vs Spec

Verified against merge commit `6a6312db0` (8 files, +915/-21). **3/3 shipped.**

| Deliverable (as executed) | Verdict | Evidence |
|---|---|---|
| D1 — derive gate bundles from real bundle dirs | shipped, exceeded | New `derive_gate_bundles.py` (+198) + `test_derive_gate_bundles.py` (+179): a bundle is derived only when `marketplace/bundles/<b>/` actually exists; otherwise the path lands in `unresolved[]` with a diagnosable WARNING. ADR-009 fail-closed still applies to *genuine* quality-gate failures. **The seam gated its own PR cleanly** — dogfooded |
| D2 — complete, count-free roster | shipped, larger | `dispatch-inline-split.md` (+52/-…): **25 steps** now classified exactly once (13 dispatched / 12 inline); **all four count claims removed**; two missing dispatch-table rows added; closure invariant pinned by `test_dispatch_roster_closure.py` (+222). The spec's "prefer derivation over a corrected constant" was honoured — it went count-free, not count-corrected |
| D3 — correct the completion-record taxonomy | shipped as re-scope | `test_step_termination_contract.py` (+248), `external-step-contract.md` (+10). The structural guard D3 was chartered to build **already existed and fired correctly on the motivating run**. The "7 recurrences" resolve to **two fused causes, not one**; only cause B's authoring surface was corrected. **No eighth point-fix.** |

## The D3 refutation is the most important finding

The staged spec's own instruction was: *"if the seven are six different causes wearing one
label, say so and re-scope."* That is precisely what happened — and the narrative sharpens it
further via the lessons pass:

- The "7 recurrences" was **itself an inferred claim** (a taxonomy artifact), exactly as the
  spec's D3 flagged as a possibility.
- The lessons-capture folded PLAN-36 into `2026-07-21-22-001` as a recurrence — **now 4-for-4**
  on falsified orchestrator-inferred mechanisms in this epic — and **widened the lesson twice**:
  1. This was the **first falsified ABSENCE claim** (the guard was said to be missing; it was
     present). The prior three were falsified *presence* claims (a mechanism was asserted to exist
     and didn't hold). The failure mode is symmetric.
  2. The staged **count itself** ("7 recurrences") was an inferred claim — so even *counts* in a
     spec are hypotheses, not facts.

## Metrics and Anomalies

- Tokens: **2.06M** · Worked: **2h3m** · Wall: **9h40m** (7h37m idle — almost all in finalize, the
  API-limit window)
- ⚠ **The phase breakdown shows finalize at 7h47m wall / 22m33s worked** — a 7h24m idle gap. This
  is the merge-queue + API-limit wait, not compute; flagged only so a future retrospective does
  not read it as a cost anomaly.
- Deploy: main at `6a6312db0`; archived cleanly.
- ⚠ **Compose-time defect hit but NOT fixed (out of scope, correctly):** `phase_5.step_execution_tier`
  stamped `verify:coverage` as `per_task` while live resolution returned
  `orchestrator/exceeds_bash_ceiling` (**946s vs the 600s cap**). Obeying the stamp would have
  forced an inline run guaranteed to be killed. Already owned by lesson `2026-07-22-00-002` — the
  **third independent sighting** of the manifest-tier-under-reporting defect (PLAN-33 saw it at
  1221s, this run at 946s). That defect is now well past the plan-worthy bar (see Follow-Ups).

## Routing and Merge Behavior

- **Review**: the narrative reports the fix dogfooded — D1's seam gated its own PR. No bot
  findings noted.
- **CI/merge**: all green, merged via queue, `main` at `6a6312db0`, worktree removed.
- **Surface collisions**: none, despite PLAN-34/37/38 running concurrently. The
  `pre-push-quality-gate.md` mutual-exclusion with PLAN-35 held — PLAN-35 was correctly withheld.

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `973`, landing `landings/PLAN-36.md`)
- [x] epic.md queue row reconciled
- [x] **Three watches RETIRED** — all now owned-and-shipped by this plan:
      `quality-gate-bundle-derivation-halts-clean-tree` (D1),
      `roster-not-authoritative` (D2),
      `self-review-completion-guard n=7` (D3 — re-scoped, the family is resolved as two fused causes)
- [x] **PLAN-35 UNBLOCKED** — its mutual-exclusion with PLAN-36 on `pre-push-quality-gate.md` is
      released. PLAN-35 now needs re-grounding: #973 rewrote `pre-push-quality-gate.md` (its `:34`
      freshness prose may have moved) and added `derive_gate_bundles.py`
- [x] `verify-before-implement` → **n=4**, lesson `2026-07-21-22-001` widened (absence-claims +
      count-claims are also hypotheses)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ Manifest execution-tier under-reporting → n=3, PROMOTE.** `phase_5.step_execution_tier`
  stamps `verify:coverage` `per_task` while live resolution returns `orchestrator` — seen at 1221s
  (PLAN-33), 946s (PLAN-36), and originally flagged in the PLAN-32 run. Lesson `2026-07-22-00-002`.
  The stamp is meant as *structural* enforcement of leaf-no-background-build; under-reporting
  downgrades it to a convention the leaf only survives by re-resolving defensively. **Three
  independent sightings in two days, sibling of PLAN-20's execution-accounting work — this is the
  strongest promote-candidate now on the board.** Not staged (four running); stage next.
- **Harness-side timeout floor** (bound-ordering n=3, lesson `2026-07-22-00-001`) — still owed,
  reconfirmed by PLAN-33's 246s self-kill. Independent of the tier defect above but adjacent.
- **PLAN-35 re-grounding** — before emit, confirm where `pre-push-quality-gate.md:34` moved under
  #973 and whether `derive_gate_bundles.py` interacts with PLAN-35's build_map oracle
  consolidation (D1 of PLAN-35 makes build-decision THE oracle; #973's bundle-derivation is a
  *scope* question that should consume it, not compete). Fold that adjacency into PLAN-35's spec.
