# Run report — 060-dispatch-boundary-ledger-is-not-a-commensurable-population (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/dispatch-boundary-ledger-k8yrwg (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded by path from the bundle source (plugin notation not required):

- `cloud-plan-lane` (first action, governs the run)
- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:persona-implementer` (production code work identity)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)

No conditional skill was needed beyond these — the surface is Python production code
(`manage-metrics.py`) plus its pytest suite, with a small `.adoc`/`.md` doc-touch reconciled inline.

## D1 — GATE: the declared population (analysis only, mutates nothing)

**Which set of dispatches is the ledger's denominator meant to be?** The ledger's per-phase
coverage figure compares two counts that come from **two different producers**:

| Figure | Field | Producer | Population |
|---|---|---|---|
| Numerator | `dispatch_boundary_rows_recorded` | the boundary-file writer `cmd_record_dispatch_boundary`, one row per dispatch that **calls** `record-dispatch-boundary` | dispatches that register a boundary |
| Denominator | `subagent_samples` | `enrich`'s post-hoc transcript walk (`claude_runtime.py`), count of Task-agent returns attributed to the phase window | every dispatch enrich sampled in the window |

These are **not one population**. The numerator is the subset of dispatches whose workflow doc issues
`record-dispatch-boundary`; the denominator is every dispatch enrich found. That is the root of all
three symptoms.

### Dispatch classes — derived from the dispatching code, not from a run

Source of truth: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/call-graph.md`
(the authoritative dispatch topology) cross-checked against every `record-dispatch-boundary` call site
in the phase workflow docs. **Not** derived from any run's emitted classes — a run-derived list cannot
contain a class that never registers, which is the defect.

| # | Dispatch class (`Task: execution-context`) | Registers a boundary? | Evidence |
|---|---|---|---|
| 1 | phase-2-refine (main envelope) | **no** | no `record-dispatch-boundary` in phase-2-refine or `planning.md` |
| 2 | phase-3-outline (main envelope, + change-type LLM fallback) | **no** | no `record-dispatch-boundary` in phase-3-outline |
| 3 | phase-4-plan (main envelope) | **yes** (`--phase 4-plan`) | `workflow/planning-outline.md:468` |
| 4 | phase-5-execute (per-task envelope) | **yes** (`--phase 5-execute`) | `workflow/execution.md:216`, `phase-5-execute/SKILL.md` |
| 5 | phase-6-finalize (per-step dispatches: create-pr, post-run-review) | **yes** (`--phase 6-finalize`) | `phase-6-finalize/SKILL.md:1051` |
| 6 | q-gate-validation (shared: fires from 2-refine Step 13.5, 3-outline Step 11, 4-plan Step 9b) | **no** | never issued from the shared workflow doc |
| 7 | verification-feedback (shared: 5-execute build-runner, 6-finalize pr-comment/sonar/plugin-doctor/pr-state) | **no** | never issued from the shared workflow doc |
| 8 | research (ad-hoc, any phase) | **no** | never issued |
| 9 | enrich-module (6-finalize architecture-refresh, ×N parallel) | **no** | never issued |

phase-1-init runs **inline** in the orchestrator (no dispatch) — it is not a dispatch class and has
nothing to register.

**Two separate figures, both derived from source:**

- **Dispatch classes that exist: 9.**
- **Dispatch classes that register a boundary: 3** (phase-4-plan, phase-5-execute, phase-6-finalize).

So **6 of 9 dispatch classes register no boundary.** The plan's HYPOTHESIS that "the two named phases
(refine, q-gate-validation) are the complete set" is confirmed to be a **FLOOR, not the set** — the
real non-registering set is `{phase-2-refine, phase-3-outline, q-gate-validation,
verification-feedback, research, enrich-module}`.

### The fork: is the class omission the mechanism behind the impossible ratio? — **REFUTED**

The impossible ratio is `dispatch_boundary_rows_recorded > subagent_samples` (numerator **exceeds**
denominator — over-coverage). The class omission makes the numerator **smaller** (fewer boundary
rows than dispatches), i.e. it drives `rows < samples` (**under**-coverage), the opposite direction.
So the omission **cannot** produce the over-coverage ratio.

The two populations do **not** differ by "exactly the non-registering classes": they also differ by an
**accumulation axis**. `cmd_record_dispatch_boundary` always **appends** to the per-phase boundary
file, which persists across re-entries/resume, while `subagent_samples` is a single enrich-window walk
(`claude_runtime.py`). On a finalize loop-back or a resumed run the numerator accumulates while the
denominator reflects one window → `rows > samples`. This is the plan's flagged second cause (the
"resumed run" HYPOTHESIS), independent of the omission.

**Consequence (drives D2/D3):** fixing the omission (D3) does **not** close the impossible ratio (D2).
They are separate defects and get separate fixes — exactly as the plan warned. D3 declares the
excluded classes (which explains the `rows < samples` shortfall); D2 makes `rows > samples` a loud
failure (which the omission never explained).

## Deliverables

Per deliverable: what was done, in which commit, and its verification state. _(filled in as the run proceeds)_

- **D1 — GATE**: complete, analysis above. Mutates nothing. Class count 9, registering count 3, both source-derived.
- **D2**: _pending_
- **D3**: _pending_
- **D4**: _pending_
- **D5**: _pending_

## Build gate

_(filled in at Step 5)_

## Findings

_(filled in from the verification sub-agent, CI, and PR review)_

## Reviewer participation

_(filled in at Step 7/8)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at close)_

## What have we learned (Step 9)

_(filled in at close)_

## Residue

_(filled in at close)_
