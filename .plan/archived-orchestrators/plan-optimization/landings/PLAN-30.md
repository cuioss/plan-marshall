# Landing Analysis: PLAN-30 — Orchestrator Terminal-Title Push Coverage

epic: plan-optimization
workstream: WS-10
pr: #967 (`f22d9c20f`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `f22d9c20f` (11 files, +103/-40). **2 deliverables as executed**
(the staged spec listed 3; D3 "preserve the close/archive restore semantics" was absorbed into
D1's rewiring rather than shipping as a separate unit — recorded as executed, not inferred from
the spec).

| Deliverable (as executed) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — state the repaint rule ONCE in `orchestration-model.md`; rewire the 4 already-pushing verb docs to reference it | shipped | `orchestration-model.md` (+18/-1) now carries the canonical rule; `init.md` (+6/-3), `resume.md` (+4/-3), `close.md` (+4/-3), `archive.md` (+4/-3) reduced to references. This is the **root-cause fix** the spec asked for — the "session-opening verbs" mis-cut is gone, stated once so a future verb inherits it |
| D2 — add the entry-point push to the 4 workflow docs covering the 5 un-pushing verbs | shipped | `orchestrate.md` (+23/-…, covers BOTH `status` and `next`), `analyze.md` (+27/-…), `decompose.md` (+23/-…), `lessons-handling.md` (+7). All five previously-uncovered verbs now push |

**Scope grew 6 → 11 files, twice, both for real reasons and both operator-approved:**

1. **`close.md` + `archive.md` + `orchestration-model.md`** — the same wrong sentence lived in more
   places than the spec enumerated, and the standard was the correct canonical home. This is the
   *right* kind of growth: the spec's D2 asked for the rule to be stated once, and honouring that
   properly required the standard.
2. **`platform-runtime/SKILL.md` (+2/-1) + `standards/contract.md` (+25/-3)** — caught by
   **pre-submission self-review**, not by a bot: the four new `--store orchestrator --slug`
   invocations relied on flags that were **implemented in argparse but absent from the documented
   contract surface**. Fixed inline.

**The contract-drift catch is the most valuable output of this plan.** Lesson
`2026-07-21-17-002` records the generalizable rule: *the first external reliance on a flag is the
trigger to verify the contract surface, not just the implementation.* PLAN-30 was itself the first
external consumer of those flags — the drift had been latent since the seam was built.

## Metrics and Anomalies

- Tokens: **1.5M** — the cheapest WS-10 landing to date (cf. PLAN-24 3M, PLAN-26 3.1M, PLAN-28 3.9M)
- Duration: **50m17s** — likewise the fastest
- Finalize: 20/20; plugin-doctor clean (2 skills gated, 0 issues / 30 rules); self-review **1 finding
  found and fixed inline**; `finalize-step-simplify` 0 edits
- Docs-only footprint confirmed working: pre-push quality-gate reported **0 bundles, no buildable
  module** — the CI footprint gate behaved exactly as PLAN-17 (#948) intended
- Deploy: 1105 files → **v0.1.1177**
- Anomalies: none in execution

## Routing and Merge Behavior

- **Review**: **0 comments; all 3 bots settled.** Review-retrospective had nothing to compare. The
  only finding on this plan came from the *local* self-review gate — a datapoint for the standing
  observation that local gates have repeatedly outperformed the bots on docs/contract work
  (cf. PLAN-13 #950).
- **CI/merge**: all checks green, rebased, merged, cleanup complete. `main` at `f22d9c20f`.
- **⚠ SURFACE COLLISION — the first observed in this epic, and my disjointness call is implicated.**
  PLAN-26 (#964) landed mid-flight and collided with PLAN-30's self-review fix: **both rewrote the
  same `push-title-token` row** in `platform-runtime/standards/contract.md`. #964 documented the
  `/dev/tty` fallback channel and `pushed: false` / `reason: no_controlling_tty`; PLAN-30
  documented the missing `--store`/`--slug` flags. Operator chose the combined resolution and both
  changes are in the merged tree, along with #964's new session-teardown op and the 21→23 op count.
  - **The disjointness verdict was correct AT EMIT TIME** (PLAN-30 = orchestrator workflow docs;
    PLAN-26 = platform-runtime) **and was broken by in-flight scope growth**, not by a bad call.
  - **This is a genuine gap in the surface-disjointness model**: it is evaluated once, at emit,
    against the *declared* surface — nothing re-checks when a plan's scope legitimately grows into
    another live plan's territory. Recorded as a new watch.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated (status `shipped`, pr `967`, landing `landings/PLAN-30.md`)
- [x] epic.md queue row reconciled from status.json
- [x] **PLAN-31 UNBLOCKED** — its ADJACENT-to-live-30 hold is released. ⚠ But PLAN-31 now REQUIRES
      re-grounding: it targets `analyze.md`, `decompose.md`, AND `orchestration-model.md`, and
      **#967 just rewrote all three**
- [x] New watch opened: disjointness is evaluated once at emit and is not re-checked on scope growth
- [x] Watch `composed-manifest-snapshot` — **PLAN-30 did NOT strand** (see Follow-Ups)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **✅ Verification-note discipline VINDICATED.** The spec forbade verifying by looking at the tab
  and required asserting the invocation per verb doc. That is exactly what happened — and **the tab
  is still blank**, because this session has no controlling terminal (`title_reset_failed` at
  archive is the same root cause). Had the plan verified visually it would have reported a false
  failure and possibly "fixed" a non-defect. **Keep this pattern for any plan whose effect is
  unobservable in the executing environment.**
- **`composed-manifest-snapshot`: PLAN-30 did NOT strand.** `lessons-housekeeping` ran at
  **position 2** (0 removed / 0 promoted / 110 retained), i.e. in the pre-merge settle band. This
  is *unexpected* — PLAN-30 was predicted to strand as a pre-#962 composition. Most likely its
  manifest was composed after `cd931fb63` despite launching earlier, or it was recomposed on the
  sync-baseline rebase. **Refines the watch**: the boundary is manifest-composition time, not
  plan-launch time, and a rebase may recompose. PLAN-32 remains the clean control.
- **Contract-drift class is broader than this instance.** Lesson `2026-07-21-17-002` is about
  argparse-implemented-but-undocumented flags. Worth a targeted sweep: how many other
  `platform-runtime` / manage-* flags are implemented but absent from their documented contract?
  Candidate for a future spec — NOT staged now (queue saturated, and the sweep needs scoping).
- **Version debt**: `marshal.json` 0.1.1163 vs **0.1.1177** — `/marshall-steward` + session restart
  owed; executor regenerated four times today.
