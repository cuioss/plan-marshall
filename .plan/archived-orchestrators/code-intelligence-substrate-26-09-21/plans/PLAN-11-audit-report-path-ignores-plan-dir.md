# PLAN-11: Auditor Integrity — a Wrong Report Path, and Superseded Plans Counted as Deliveries

epic: code-intelligence-substrate
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

`audit.py`'s `write_persisted_report` derives its output path from `Path.cwd()` and **ignores the
`--plan-dir` argument it is given**. A prior task (TASK-11 on PR #1043) fixed **only the test side**,
so the surface went green while the production defect stayed live.

⚠ **This is the fix-the-test-not-the-call inversion**, and it is the reason this is a separate plan
rather than a note: from the outside, a test-side fix is indistinguishable from a real fix at the
reporting layer. Reports are still written to the wrong location whenever cwd differs from the plan
directory — which is the normal case under worktrees.

## Deliverables

1. Make `write_persisted_report` honour `--plan-dir` for its output path rather than deriving from
   `Path.cwd()`.
2. A test that fails against the current production path — ⛔ **it must exercise the real resolver
   with a cwd that differs from `--plan-dir`.** A test that passes only because cwd happens to equal
   the plan dir reproduces the exact defect being fixed.
3. Sweep `audit.py` for **sibling** `Path.cwd()` derivations. ⛔ **Derive the population — do not
   trust this spec's single named site.** One instance was reported; a reported instance is a sample.

## Claim Labels

- **HYPOTHESIS (forwarded lead, NOT orchestrator-verified)**: `write_persisted_report` derives its
  path from `Path.cwd()` and ignores `--plan-dir`; TASK-11 fixed only the test side. Source:
  `exploration-share-is-unmeasured-002` via `truthful-signals-004`, origin PLAN-99 / PR #1043.
  ⛔ **This orchestrator did NOT read `audit.py`.** Confirm/refute at the project-local auditor
  `audit.py` § `write_persisted_report` (verify-at-outline).
- **HYPOTHESIS**: the defect is live on `main` at the time of staging — PR #1043 merged, and the
  message states the production half was left unfixed. Re-verify against HEAD before scoping; if a
  later plan repaired it, **close this plan as already-fixed rather than re-fixing it.**
- **Verify-first clause**: deliverable 3 asserts sibling sites may exist. That is an asserted
  *possibility*, not an asserted presence — resolve it by enumeration, and record "none found" as a
  legitimate and complete outcome.

## Expected Surface

- **HYPOTHESIS**: the project-local auditor `audit.py` § `write_persisted_report` and any sibling `Path.cwd()` derivations (verify-at-outline)
- **HYPOTHESIS**: the auditor's test module — the test corrected by TASK-11, which must be re-pointed at the production path (verify-at-outline)

## Dependencies and Sequencing

- **Depends on**: none. Small, surgical, independently runnable.
- ⛔ **Collides with PLAN-CIS-016 `auditor-detector-integrity` on `audit.py` — NEVER PAIR.** Run this
  one **first**: it is a small live production defect, while PLAN-CIS-016 is a 6-deliverable detector
  overhaul that would otherwise absorb it.
- ⭐ **Why this is its own plan rather than a PLAN-CIS-016 deliverable**: the forwarded message
  recommended PLAN-CIS-016 as the natural home *and* flagged that PLAN-CIS-016 is already at the
  six-deliverable split guard. Growing a plan that is already at the guard, to absorb an unrelated
  production fix, is the failure the guard exists to prevent. Splitting it out keeps both small.
- ⚠ **Cross-epic**: `truthful-signals` filed this as a candidate-lesson, so it may allocate it too.
  ⛔ **Confirm it has not staged a plan for `audit.py` before emitting** — per-epic disjointness
  cannot see across the boundary and this is exactly the class of collision it misses.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-11-audit-report-path-ignores-plan-dir.md"
```

## Inherited Inbox Evidence — SECOND DEFECT FOLDED IN (2026-07-29, `truthful-signals-007`)

⛔ **A SUPERSEDED PLAN IS INDISTINGUISHABLE FROM A SHIPPED ONE IN THE ARCHIVED CORPUS.**

`archive` stamps `current_phase: complete` — **the only terminal value the lifecycle has.** The sole
distinguisher is `status.metadata.archived_reason` (here `closed_superseded`). Anything keying on
`complete` alone reads a superseded plan as a shipped one.

**OBSERVED — verified at HEAD by the forwarding orchestrator, not message-supplied:**
1. `audit.py` **enumerates every archived subdirectory** under `.plan/local/archived-plans/{plan_id}/`.
2. ⛔ **`archived_reason` appears NOWHERE in the entire `audit-archived-plan-retrospectives` skill.**
   No filter, no carve-out, no branch.
3. `archived_reason` *does* have consumers elsewhere (`manage-status/_cmd_lifecycle.py`,
   `plan-doctor`) — the field is real and read; **the auditor simply does not read it.**

**What it corrupts, concretely.** PLAN-105 shipped **nothing** (PR #1046 closed, never merged), yet
carries **3.1 M tokens / 2h15m worked / 14h6m wall**. All 23 checks will score it as a delivery —
token-economics, exploration-share and lane-lever-effectiveness count 3.1 M as delivery cost;
`affected_files_recall` scores a plan with no footprint by design; PR-merge velocity computes a merge
time for a PR that was never merged; scope-estimate accuracy compares estimate against work that
never shipped.

⭐ **THIS IS THE CHEAP MOMENT AND IT WILL NOT RECUR: PLAN-105 is the FIRST superseded plan in the
corpus — a population of ONE.** Fix it now and the historical series stays clean. Fix it after
several land and every figure already quoted from the corpus must be re-derived, including figures
this epic has itself relied on.

### Additional deliverables

4. **The auditor filters on `archived_reason`, not on directory presence.** A non-shipping archived
   plan is either excluded from delivery-cost checks or reported in **its own bucket** — never
   silently summed.
5. ⛔ **Do NOT special-case the string `closed_superseded`.** Derive the **shipping predicate** (a
   merged PR / a real footprint) and let every non-shipping reason fall out of it. A hardcoded list
   mirroring a set defined elsewhere is the archetype this programme has recorded 5+ times, and it
   would guarantee the next terminal reason reintroduces this defect.
6. **Report the exclusion count separately from the examined count.** A corpus check that silently
   drops rows is the same failure in the opposite direction.

⚠ **Related, deliberately NOT scoped here**: the lifecycle has **no terminal value for "ended without
shipping"**. Adding one is a larger change and is **not required** to close the measurement hole. If
this epic's direction work touches lifecycle vocabulary, reconcile the two rather than solving twice.

⛔ **AT 6 DELIVERABLES THIS SPEC IS AT THE SPLIT GUARD.** The natural cut is **path resolution**
(D1-D3) from **corpus filtering** (D4-D6) — they share only the file. ⭐ **But D4-D6 are the
time-critical half** (population of one, growing), so if it splits, **the corpus-filtering half runs
FIRST**, inverting the current deliverable order. Re-evaluate at outline.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write.
