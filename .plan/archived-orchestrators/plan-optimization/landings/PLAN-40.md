# Landing Analysis: PLAN-40 — Orchestrator Standard Hardening

epic: plan-optimization
workstream: WS-10
pr: #981 (`dfc4ac15c`)

> Landing record. Claims verified against the merge commit, not the finalize report.

## Deliverable Fidelity vs Spec

Verified against `dfc4ac15c` — **7 files, +142/−30, documentation-only. 5/5 shipped.**

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1+D2 — verify-first promoted to a named `orchestration-model.md` section, extended to Expected-Surface + finding-sharpenings | shipped | `orchestration-model.md:135-138` — "every claim labelled `OBSERVED` or `HYPOTHESIS`… a HYPOTHESIS carries a named confirm/refute artifact (a file plus the symbol within it), marked verify-at-outline; a HYPOTHESIS with no named artifact MUST NOT be serialized." Attaches to the **act of serializing an inference**, not a document type (spec / ADR / escalation resolution). |
| D3 — landing analysis ends with a standing proactive emit, queued to an operator-set parallelization scope, gated by surface-disjointness + prep-readiness | shipped | `orchestrate.md` (+45/−), `analyze.md` (+9), `init.md` (+39, the `parallelization_scope` AskUserQuestion at start) |
| D4 — single-source spec template + one-line hand-off (**orchestrator half only**) | shipped | `templates/plan-spec.md` (+45/−). The phase-1-init half was **gated out** — see PLAN-41 below. |
| D5 — effort dimension on the Dispatch Decision Rule (read-only analysis may raise the tier; still gathers/verifies + returns a structured verdict only) | shipped | Dispatch Decision Rule extended in `orchestration-model.md` |
| D6 — ledger write-boundary documented, Status Trail invitation removed | shipped | write-boundary in `orchestrate.md`/`decompose.md`; `status-lifecycle.md` (+10) records that the orchestrator owns `.plan/local/orchestrator/{epic}/` exclusively |

## The plan proved its own thesis — twice, live

1. **D4's hypothesis was refuted by its own gate.** The spec proposed a one-line
   `task="implement {spec_path}"` hand-off as *sufficient*. Verify-first (the very discipline D1
   promotes) forced the check: **phase-1-init `SKILL.md:290-294` Step 4 says "Use description
   directly / No additional context"** — it never reads the referenced spec, its file-reading
   pre-flight is lesson-only, and refine merely existence-checks paths. So the one-liner **silently
   loses the brief**. The hopeful answer was refuted at the gate; the fix was correctly **deferred to
   PLAN-41 rather than smuggled in**.
2. **A plan about verifying claims nearly shipped an unverified one.** Two review loop-backs caught
   **six** genuine defects in the plan's *own new text*, including a **deadlock**: the new
   "Prep-ready" admission test would have made verify-first specs **permanently unemittable** (a spec
   naming a HYPOTHESIS could never pass its own prep gate). Caught pre-merge. This is the strongest
   possible datapoint for the discipline — the standard's first user was the standard itself.

## Three lessons — each mechanism verified against source, not inferred

- **`2026-07-22-16-002`** — a **docs-only plan can never satisfy `pre-commit-verify-freshness`**: the
  exemption checks the **compose-time step list**, not the **runtime skip outcome**. Unblocked
  honestly by running whole-tree module-tests (green, 3×), never `--force`. → **finalize-machinery /
  checks-the-wrong-thing**; candidate (a docs-only plan tripping a gate it structurally cannot pass).
- **`2026-07-22-16-003`** — **`resolve-test-scope`, a query verb, writes a `kind=build` ledger row
  with `status: success`** — a pure scope query flips the freshness gate stale→fresh with **no build
  run**. Caught a live false-fresh window. → **confident-signal-hides-a-caveat (n+1)** AND adjacent
  to **live PLAN-35** (freshness-gate / build-status oracle) — a query verb minting a build-success
  row is the same false-fresh neighbourhood; flag as PLAN-35 input, do not force-merge.
- **`2026-07-22-16-004`** — the plan **authored an emit contract whose own command was unroutable**
  (no `task=` → resolves to `action=list`). Caught by self-review, not outline or Q-Gate. Fixed
  in-plan; the D3 emit contract now carries `task=`. Closed.

## ⚠ Off-spec: a real finalize-contract violation, left uncommitted (not papered over)

`.plan/project-architecture/default/enriched.json` is **uncommitted on main** — the
preference-emitter's architecture hint. Root cause verified: **`finalize-step-preference-emitter` is
`order: 80`** (after `branch-cleanup` merges at 70) **yet writes a tracked file**, violating
`phase-6-finalize/standards/source-edit-pushability.md` (source-editing steps must run pre-merge).
The executor **refused all three wrong outcomes** — no silent revert (the hint is valid), no
direct-commit-to-main (violates full-PR-flow), no paper-over — and left it dirty with the diagnosis.
Fix shape: either the step moves to `order < 10`, or its architecture-enrich sink is declared
non-source. **Symptom** (the dirty file) is owed a follow-up PR per operator; **root cause** is
staged as **PLAN-44**.

## Reconciliation Actions

- [x] status.json `plans[]` → `shipped`, pr `981`, landing `landings/PLAN-40.md`
- [x] **PLAN-41 staged** — the deferred phase-1-init half of D4 (orchestrator's job per D6; the plan
      correctly refused to stage into my ledger)
- [x] **PLAN-44 staged** — finalize preference-emitter order violates source-edit-pushability
- [x] Watch **confident-signal-hides-a-caveat** — reinforced (lesson 16-003, resolve-test-scope
      build-success row; n=4 with false-green build / PLAN-42 / PLAN-43)
- [x] Watch **checks-the-wrong-thing** (compose-time list vs runtime skip; lesson 16-002) — logged as
      candidate, adjacent to the finalize-machinery family
- [x] Lesson 16-003 flagged as **PLAN-35 input** (freshness-gate adjacency)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **PLAN-41** (phase-1-init single-source ingestion) — makes the one-line hand-off actually carry the
  brief; without it D4's orchestrator half is a hand-off to a reader that discards it.
- **PLAN-44** (finalize preference-emitter ordering) — recurs on every plan whose preference-emitter
  promotes an architecture hint; the follow-up PR only cleans the symptom.
- **Lesson 16-002** (docs-only vs pre-commit-verify-freshness) — unstaged candidate; same
  checks-the-wrong-thing shape as PLAN-35's oracle work and the finalize-machinery family.
