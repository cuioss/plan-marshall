# PLAN-CIS-045: The Executor Generator Fails Open, And Its Fixtures Are Structurally Unable To Notice

epic: code-intelligence-substrate
workstream: WS-05

> Staged 2026-08-09 from the PLAN-CIS-032 landing (#1127), inbox `-001` and `-007`.
> Both arms are **first-party from that run**, and one of them was recovered by hand
> mid-finalize. Self-sufficient spec.

## Objective

Two defects, one root: **the executor's surface derivation cannot tell "derived nothing" from
"derived everything", and the suite that guards it is built from fixtures that cannot express the
difference.**

**A — the generator is fail-open at the last gate.** At the end of #1127's finalize, the documented
on-main executor regeneration reported `status: success` while producing a **surfaces-less
executor**. Probed live, `manage-tasks nuke` fell through to argparse *after* spawn instead of
being rejected pre-spawn — **the plan's own headline guard was not live on main despite a green
sync and a green regen.** Recovery required running the merged-source generator directly
(`--marketplace --marketplace-root . --force`), which derived **106 surfaces over 148 scripts**.

⛔ **The only observable distinguishing the two outcomes is the ABSENCE of a surface-stats line,
and nothing consumes absence.** ⭐ The same shape was hit independently by a fix agent during
phase-5, so it is a **recurrence inside a single plan**, not a one-off.

**B — the fixtures cannot see a strip-the-attribute defect.** #1127's own execute and finalize
found **four** defects in the guard it shipped — every one a valid call refused or an operator
misdirected — and **every one caught by running the guard live, none by the test suite**:

| # | Defect | Why the suite missed it |
|---|---|---|
| 1 | `--help` refused on **every** script (`reason=unknown_flag, accepted=[]`) | no fixture had an empty flag set |
| 2 | a leading top-level flag desynchronised the parser walk — same two accepted tokens returned for *different* verbs, so the walk never left ROOT | no fixture invocation started with one |
| 3 | short `-h` still refused after the `--help` fix | *"zero hits for the token across the test tree"* |
| 4 | the `unknown_flag` corrective advertised a set **contradicting its sibling corrective** on the same node — an operator following it is refused on the next attempt | no fixture declared a flag that was also universal |

⛔⛔ **The plan states the root cause exactly**: *"it still shipped past a green synthetic suite,
**because every fixture surface happened to declare at least one flag**."* A hand-built fixture is
written to be *representative*, therefore **populated** — which makes the whole class *"the
derivation strips / omits / mis-attributes attribute X"* **structurally invisible**, because X is
only absent on a surface nobody would hand-write.

## ⭐ Why this is the epic's business and near the top of WS-05

This is the epic's two standing rules colliding in one place: **every set-guarding detector must be
population-derived**, and **probe the objective live**. ⭐ **And arm A is a SECOND, independent
mechanism by which the on-main executor silently disagrees with merged source** — the first being
the plugin-registry pin inversion the epic checks before every launch. A pre-launch pin check does
not cover it, because this one manufactures a green *finalize* over an inert guard.

⭐ **Self-exercisability is better than the epic assumed, and that is usable.** #1127 refuted its
own non-exercisability premise in flight (decision.log `e4341f`): **phase-5 generates a
worktree-bound executor**, so regenerating inside a run exercises the guard end-to-end against 148
real notations. **The boundary is main-checkout-and-cache-scoped, not absolute.**

## Deliverables

1. **D1 — fail a regeneration that derives zero surfaces where the previous one had surfaces.**
   `generate_executor` already computes `surfaces_reused` / `surfaces_derived`, and
   `read_previous_surfaces` already knows the outgoing entry count. When previous `N > 0` and the
   new generation emits `0` (neither derived nor reused), **exit non-zero rather than reporting
   success.** ⛔ **Emit the surface-stats line UNCONDITIONALLY, including the zero**, so consumers
   assert on a present value instead of inferring from an absent one. ⭐ *An absence nothing
   consumes is not a signal* — state that as the contract, not as a comment.
2. **D2 — derive the fixture corpus from the real surface index.** The generator already produces a
   148-script / 106-surface index. A test that walks it and asserts every registered notation's
   `--help`, `-h`, and declared-flag invocation is accepted is **population-derived**, so it fails
   the moment the derivation drops an attribute — which four hand-built rounds could not do.
   ⛔ **This is the standing population-derived rule applied to the guard's own fixtures**; copy the
   `test/_shared/_dispatch_roster.py` shape and **publish the population size**.
3. **D3 — make a regenerate-and-dispatch live smoke part of shipping a validator change.** All four
   defects were caught that way and none by the suite. ⛔ **This is NOT "add more unit tests"** — it
   is evidence that the synthetic and live surfaces differ in a way the suite cannot self-detect.
   The smoke must include **a help spelling and a leading top-level flag**, the two shapes that
   actually bit. ⚠ It belongs in the deliverable, not in a reviewer's judgement.

Three deliverables — well below the split guard.

## Claim Labels

- **OBSERVED (first-party, this orchestrator, post-merge on main)**: the guard IS live and the
  corrective IS on **stdout** — `manage-tasks nuke` returns the `invalid_invocation` TOON with a
  21-verb accepted set, and it **survives `2>/dev/null`**. ⇒ **Arm A is about the regeneration
  path, not about the shipped guard**, which works. Do not conflate them.
- **OBSERVED (#1127 decision.log `5f800e`, WARNING)**: the false-green regeneration and the manual
  recovery, with `status.json phase_steps` recording `done` only *after* the hand recovery.
- **OBSERVED (#1127 decision.log `b5604b`)**: the healthy shape for comparison — 148 registered,
  106 derived, 0 reused, 42 not derivable.
- **OBSERVED (#1127 qgate findings `dc73da` / `6d981f` / `cdbb40` + decision.log `438350`)**: the
  four false-rejection defects, each with a live reproducer and live verification.
- ⭐ **OBSERVED, and worth preserving as a positive control**: the **repair** half worked every
  time — fail-first proof plus matched negative controls on each fix (`6d981f`: three positive and
  three matched negative so the fix could not read as disabling validation; `cdbb40`: an omission
  control plus a required-subset-of-declared non-contradiction invariant). ⇒ **The gap is
  DETECTION, not remediation** — do not spend this plan hardening the repair path.
- **HYPOTHESIS**: that D2's population-derived corpus is affordable at 148 scripts × 3 invocations.
  ⚠ The derivation probes `--help` per parser node under a per-probe timeout and a shared
  wall-clock deadline, so **a full-population test may be too slow for the edit-time gate**.
  **Measure at outline**; if it is, the corpus belongs in a slower tier, ⛔ **not silently sampled**
  — a sampled population-derived test is a hand-built fixture with extra steps.
- ⛔ **Verify-first**: re-ground arm A against HEAD before scoping. #1127 shipped changes to
  `generate_executor` guard ordering as in-radius consequences, so **part of D1 may already exist.**

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/tools-script-executor/` — `generate_executor` and the `execute-script.py.template`
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py` — the derivation (new in #1127)
- **HYPOTHESIS**: `test/plan-marshall/tools-script-executor/` — the fixture corpus (verify-at-outline)
- **HYPOTHESIS**: `test/_shared/_dispatch_roster.py` — the population-derived shape to copy (read, not edited)

## Dependencies and Sequencing

- **Depends on**: nothing. `PLAN-CIS-032` shipped the surface this repairs.
- ⛔ **Never pair with `PLAN-CIS-043`** — both are WS-05 detector-integrity plans, and both change
  what a "population-derived fixture" means in this repo. **Land one, then read it.**
- ⚠ **Adjacent to the plugin-registry pin inversion** (§ Open Defects) — same failure *class*
  (on-main executor disagrees with merged source), different mechanism. ⛔ **Do not merge the two**:
  the pin inversion is a registry-vs-cache problem the operator repairs by hand, this is a
  generator fail-open. **A fix for one does not cover the other, and reporting them together would
  hide that.**
- ✅ Disjoint from every WS-01/02/03/04/06 plan.

## Anti-goals

- ⛔ **Do not harden the repair path.** It already works; the gap is detection.
- ⛔ **Do not add hand-written fixtures for the four known defects.** That is the exact move that
  produced the blind spot — it fixes four instances and leaves the class.
- ⛔ **Do not sample the population under D2.** A sampled population-derived test is a hand-built
  fixture with extra steps.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-045-generator-fails-open-and-its-fixtures-cannot-see-it.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
