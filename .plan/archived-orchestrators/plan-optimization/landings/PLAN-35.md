# Landing Analysis: PLAN-35 — Build-Decision Oracle Consolidation

epic: plan-optimization
workstream: WS-10
pr: #985 (`287c3c86d`)

> Landing record. Claims verified against the merge commit, not the finalize report.
> **This is the epic's final plan — plan-optimization drains here.**

## Deliverable Fidelity vs Spec

Verified against `287c3c86d` — **37 files, +2031/−1655. 5/5 shipped.**

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — inventory every build/no-build decision point (GATE) | shipped | falsified **two of its own premises** (see below) — the gate earned its keep |
| D2 — single-authority design + classifier boundary | shipped | ADR-004 amended: "**`build-decision` is the sole build/no-build authority**"; `decision-rules.md:288` fences the file-role bucket from the verdict |
| D3 — migrate every site, retire variants | shipped | `lint_only` deleted entirely; the shape-based build **reason** `documentation_only` removed; `aspect-classify`'s build-deciding role gone; Row 3 `docs_only` dropped from the decision matrix (now six rows); `should_execute_build`'s `canonical_command` became an **optional label** not an input |
| D4 — compose-time contradiction guard | shipped | `check_build_verdict_consistent` in `manage-execution-manifest.py` + `_manifest_validation.py` + `decision-rules.md`; `test_build_verdict_contradiction_guard.py` (+307) with explicit non-empty-footprint clause + anti-vacuity tests |
| D5 — PLAN-31-shaped end-to-end regression | shipped | `test_plan31_docs_only_deadlock_regression.py` (+262); `test_aspect_step_dropping.py` (−374) and `test_read_verification_steps_cache.py` (−120) retired |

## ⚠ Verification nuance (deliverables AS EXECUTED, not as phrased)

The finalize report said "`documentation_only` / `lint_only` are deleted." Ground truth: **`lint_only`
is gone; `documentation_only` survives as a file-role BUCKET name** (`manage-execution-manifest.py`
returns it for a config-only/empty path list). What was deleted is its role as a **build-decision
reason**. `decision-rules.md:288` now states this explicitly: "`documentation_only` is a **file-role
bucket name, not a build verdict**." The distinction is the whole point of the consolidation — not an
over-claim, but the landing records the precise boundary.

## The gate paid again — D1 falsified two premises (verify-before-implement, n+1)

- **`canonical_verify_inactive` is NOT a build oracle** — it gates on role membership, so it was left
  alone rather than migrated speculatively.
- **`pre_push_quality_gate_inactive` already called `should_execute_build`** — the defect was
  **mis-consumption** (hardcoded `'quality-gate'`, a logged reason the verdict never returned), not
  re-derivation. The fix was to consume correctly, not to migrate.
  The binding `verify-before-implement` practice working as designed: the inventory refused to migrate
  what only looked like a fourth oracle.

## ⚠ Two off-plan findings — one serious

1. **baseline-reconcile silently persists a merge commit** (lesson `2026-07-22-21-001`) — its
   `--no-emit` probe left a **merge commit as the feature-branch HEAD**, contrary to its documented
   contract "always aborted before any working-tree mutation persists." Misfires only on the
   `auto_reconciled: true` path. Caught incidentally in a `git worktree list`; reset and rebased
   properly — but **unnoticed it would have force-pushed a merge commit into a squash-merge repo,
   unverified.** doc-contract-divergence + a silent mutation the contract says cannot happen →
   **staged as truthful-signals PLAN-52.**
2. **Diff-scoped sweep misses the tree** — three passes (phase-5, self-review ×4, CodeRabbit ×2) were
   needed to fully retire the vocabulary, because the sweep was scoped to the diff not the whole tree.
   Folded into lesson `2026-07-18-05-002` → truthful-signals **diff-scoped-sweep** watch.

## Reconciliation Actions

- [x] status.json `plans[]` → `shipped`, pr `985`, landing `landings/PLAN-35.md`
- [x] **plan-optimization DRAINED** — 21 shipped, 0 running, 0 staged → archive via #937
- [x] **truthful-signals PLAN-50 unblocked** — the `manage-execution-manifest` rewrite PLAN-35 owned
      has landed; re-ground `_manifest_lanes.py` against `287c3c86d` before emitting PLAN-50
- [x] **truthful-signals PLAN-52 staged** — baseline-reconcile merge-commit persistence (lesson `21-001`)
- [x] Watch **diff-scoped-sweep** — recorded (lesson `2026-07-18-05-002`)
- [x] Candidate (e) `resolve-test-scope` build-row false-fresh — **re-assess** against the new single
      authority: build-decision is now the sole verdict, so a spurious build-success ledger row may no
      longer flip the gate; confirm at that candidate's grounding
- [x] merge-mutex stale entry (`modernize-python-toolchain` held the FIFO front, lock free) released
      after operator-confirmed halt — resolved, no action

## Epic Close

plan-optimization has shipped its full wave (21 landings) and its successor `truthful-signals` is
live. Close + self-archive via #937.
