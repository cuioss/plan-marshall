# Landing Analysis: PLAN-14 — scoped-whole-tree-module-tests

epic: plan-optimization
workstream: WS-04
pr: 942 — https://github.com/cuioss/plan-marshall/pull/942 (merged `e2d0f45f8`)

> Landing record for one shipped plan. Claims verified against ground truth: PR #942 confirmed
> `state: merged` via the CI abstraction, merge commit `e2d0f45f8` present on `origin/main`.

## Deliverable Fidelity vs Spec

The staged spec carried a single deliverable **D1** (match-the-whole-tree-authority-or-warn), with the
explicit outline instruction to confirm the match-or-warn trade-off. At outline the premise was
**re-grounded**: discovery found the pre-push quality-gate is **mypy + ruff only (no pytest)**, so
PLAN-08's 33-failure regression was never inside that gate's scope. At operator direction (option b —
close the real gap, light→deep escalation) D1 was implemented as a real callable divergence seam plus a
finalize whole-tree module-tests gate, decomposed into three shipped parts.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — gate must match whole-tree authority or warn on divergence | shipped-modified (premise re-grounded; light→deep) | `_test_scope_divergence.py` + `pyproject_build resolve-test-scope` subcommand + unit tests |
| D1.2 — wire the divergence gate into finalize | shipped (as decomposed) | `pre-push-quality-gate.md` match-or-warn, seam-gated |
| D1.3 — regression fixture | shipped-as-specified | behavioral scoped-green / whole-tree-red fixture |

Net: 3/3 shipped; the spec's single D1 expanded into a real seam (not just a doc warning), matching the
spec's "match-or-warn" trade-off while degrading the *local* gate to a loud warning (see below).

## Metrics and Anomalies

- Tokens: ~2.2M (partial capture — phase-2-refine and phase-3-outline metrics partial)
- Duration: 5h12m wall
- Anomalies:
  - **Whole-tree verify could not run locally** — the marshalld daemon refused submit (the inert-allowlist
    bug, this epic's known build-server watch) and the ~33-min whole-tree build exceeds the harness ceiling.
    Per the operator's "let CI verify" decision, the local gate was degraded to a loud warning and CI
    validated the whole tree — **green twice** (initial push + after review fixes).
  - **Leaf per-task verification missed real defects** — the leaf ran mypy+ruff+compile but not pytest, so
    two genuine correctness defects reached bot review (root-level path misattribution; empty-scope
    module-tests `None` command). Same "per-task verification missed pytest" experience the plan set out to
    fix — self-reinforcing.

## Routing and Merge Behavior

- Review: **Gemini + CodeRabbit each caught genuine correctness bugs** (root-level path misattribution;
  empty-scope module-tests None command) that the leaf's mypy+ruff+compile pass missed. Loop-back fixed
  all 3; re-review converged clean. One accepted simplify finding: `classify_divergence` has no production
  caller — kept deliberately as the D3 acceptance-fixture oracle.
- CI/merge: whole-tree CI green ×2; squash-merged via the **merge queue**; 21/21 finalize steps done;
  worktree removed, main up-to-date, working tree clean.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-14 → shipped, pr 942, landing recorded
- [x] epic.md queue reconciled from status.json (Ordered Queue row 14)
- [x] Watch retired — "Leaf under-scopes a breaking-change test sweep" (scoped-vs-whole-tree class) closed by this landing
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Lesson `2026-07-19-16-002`** filed (footprint classifier must fail-safe at boundaries) — captured in
  the plan's corpus; watch for recurrence, no epic action.
- **Lesson `2026-07-18-22-001` retained, NOT closed** — this plan's own per-task-verification-missed-pytest
  experience reinforced the source lesson rather than closing it. The deeper facet — *a phase-5 leaf's
  per-task verification runs mypy+ruff+compile but not pytest, so contract-breaking regressions escape to
  CI/bot-review* — is a genuine standing gap. Re-homed as a new Watch (below).
- **Build-server inert-allowlist** confirmed again as the reason local whole-tree verify degraded to a
  warning — already tracked by this epic's build-server watch and owned by the plan-server epic; upstream
  **#941** landed the marshalld registration-scope fix mid-run, so expect this to stop recurring once the
  cache carries #941.
