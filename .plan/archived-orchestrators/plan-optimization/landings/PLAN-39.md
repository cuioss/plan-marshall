# Landing Analysis: PLAN-39 — Manifest Tier Truthful Stamp

epic: plan-optimization
workstream: WS-10
pr: #980 (`39f24b3ad`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `39f24b3ad` (10 files, +320/-81). **3/3 shipped.**

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — settle hypothesis A vs B against named artifacts (GATE, mutates nothing) | shipped | commit body records A **refuted** (positive control: a real re-compose stamped `verify:coverage=orchestrator`, only a success dict can) + B **confirmed** by live reproduction (`python:coverage` read twice across one 593s build: 547s→`per_task`, 726s→`orchestrator`, no code change) |
| D2 — align the compose stamp with execute-time reality (branch B shape i) | shipped | `manage-execution-manifest.py` (+88/−), `decision-rules.md`, `manifest-schema.md`; advisory-stamp shape (i) chosen, ceiling-from-stable-input shape (ii) **declined** because it re-touches the shared `run_config timeout_get` lesson `2026-07-22-00-001` wants a floor on — convergence flagged, not absorbed, as instructed |
| D3 — regression pinning stamp-vs-live-tier against a REAL resolved shape | shipped | `test_compose_execution_tier.py` (+245) — rebuilt so it no longer monkeypatches `_resolve_step_execution_tier` at every call site (the blindness that let this ship) |

## The gate paid again — B confirmed empirically, A refuted with a positive control

This is the epic's binding `verify-before-implement` practice working as designed. D1 did **not**
reason from code shape; it ran both named artifacts:

- **A (masked resolution failure) refuted** — `_invoke_architecture_resolve` returned
  `status: success` with a populated `execution_tier` on every call; none of its seven
  `None`-causes fired. The re-compose positive control stamped `orchestrator` — a value only a
  success dict yields.
- **B (snapshot of a volatile value) confirmed** — the run-config `bash_timeout` for the same
  command crossed the 600s ceiling between two reads separated by one real whole-tree build
  (517s→547 under, 696s→726 over). The stamp was snapshotting a value that moves.
- **Rival eliminated by ground truth** — a compose-vs-execute store divergence cannot explain it,
  because `run_config.get_run_config_path` ignores its `project_dir` arg and resolves main-anchored;
  both reads hit the same `run-configuration.json`.

**The plan demonstrated its own defect while running**: phase-4 compose stamped
`verify:coverage=per_task`; the live resolve at execute time said `orchestrator` at 1068s. Under the
OLD contract the leaf would have trusted the stamp and run a 1068s build inline — the exact
leaf-no-background-build loss the stamp exists to prevent. And the 593s reproduction build was
itself auto-backgrounded by the harness after exceeding its own 547s `per_task` timeout. The defect
is not theoretical; it fired live, twice, during the plan that fixed it.

## ⚠ Two off-spec findings, both in the surface the plan touched

1. **The leaf read-site contradicted itself.** `phase-5-execute/SKILL.md:222` declared the stamp
   the routing authority while `canonical_verify.md` told the same body to re-resolve. The
   "defensive re-resolve" that saved three runs was **one doc winning over the other**, not a
   designed safety net. Both fixed in this PR (`phase-5-execute/SKILL.md` +22, `canonical_verify.md`).
   This is the **doc-contract-divergence** class again — two standards giving the same body
   contradictory instructions, the divergence invisible until one path fires.
2. **The test suite structurally could not catch this.** It monkeypatched
   `_resolve_step_execution_tier` at every call site, so no test ever exercised the compose stamp
   against a live resolve. D3's rebuild removes that blindness. Same shape as PLAN-23's marker suite
   (tests that pin the bug rather than catch it) — a **test-pins-the-defect** recurrence.

## Metrics and Anomalies

- Tokens: **2.25M** · Worked: **2h7m** · Wall: **4h46m** · all 6 phases (partial: false)
- ⚠ **finalize-step-simplify returned without calling mark-step-done** — the post-dispatch guard
  caught it (`step_record_missing`), recorded `failed`, halted; a retry recorded the outcome. This
  is the guard doing its job — noted as a finalize-machinery data point (PLAN-36 territory), not a
  new defect. lessons-capture judged it adequately covered at n=1 and declined a lesson.
- New lesson **`2026-07-22-13-001`**: the Grep/Glob tool grant is **re-sampled per envelope** —
  denied/denied/granted/denied across four dispatches in one session with no change in declared tool
  surface. That non-determinism made the documented escape hatch read as a dead end and pushed one
  envelope to carry residual coverage risk into a success criterion (resolved `accepted`); a later
  search-capable envelope closed the gap for free. Merged a recurrence into `2026-07-21-16-002`.
- Deploy: executor regenerated; **marshal.json stale (0.1.1180 vs installed 0.1.1191)** — owed
  `/marshall-steward` + session restart (accrued across the day's bundle bumps, same standing debt).

## Routing and Merge Behavior

- **CI/merge**: all green, merged via queue, `main` at `39f24b3ad`, worktree removed, tree clean.
- **Surface collisions**: none. PLAN-39 owned `manage-execution-manifest.py` uncontested while
  PLAN-40 (marshall-orchestrator) and PLAN-23 (marker detector) ran disjoint.
- **This landing frees PLAN-35** — which touches `manage-execution-manifest.py:222-332`
  (`_classify_paths_via_extensions`) and was held behind PLAN-39's ownership of that file. Re-ground
  PLAN-35 against `39f24b3ad` before emitting: PLAN-39 changed this file (+88/−), so PLAN-35's cited
  line ranges (`:222-332`) may have moved.

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `980`, landing `landings/PLAN-39.md`)
- [x] epic.md queue row reconciled
- [x] Watch **doc-contract-divergence** — reinforced (leaf stamp-authority vs re-resolve, n+1)
- [x] Watch **test-pins-the-defect** — reinforced (monkeypatch-every-callsite blindness; joins
      PLAN-23's marker suite as the second instance this epic)
- [x] Watch **tool-grant-nondeterminism** — NEW (lesson `2026-07-22-13-001`; per-envelope re-sampling
      of Grep/Glob; unowned harness behavior, same infra class as the dispatch-instability watch)
- [x] PLAN-35 unblocked-note recorded (re-ground vs `39f24b3ad` before emit)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **PLAN-35 re-ground owed before emit** — its `_classify_paths_via_extensions:222-332` citations sit
  in the file PLAN-39 just changed (+88/−); confirm the range at re-ground.
- **Tool-grant non-determinism is unowned** — lesson `2026-07-22-13-001` documents a per-envelope
  re-sampled Grep/Glob grant. Like the dispatch-instability tax, this is harness behavior beyond
  plan-marshall's code; worth surfacing to the operator as an infrastructure item, not a plan.
