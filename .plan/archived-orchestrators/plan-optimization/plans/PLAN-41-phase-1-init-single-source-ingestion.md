# PLAN-41: One-Line Spec Hand-Off Silently Loses the Brief

epic: plan-optimization
workstream: WS-10

> Staged plan spec. The **split-trigger reserved by PLAN-40 (#981) D4** — the phase-1-init half of
> single-source spec hand-off. PLAN-40's own verify-first gate **refuted** the hypothesis that a
> one-line `task="implement {spec_path}"` hand-off is sufficient, and correctly **deferred** the fix
> rather than smuggle it in (and could not stage this plan itself — writing the orchestrator ledger
> is the orchestrator's job, per D6). Staged by the orchestrator on PLAN-40's landing.
>
> **Grounded at `main` @ `dfc4ac15c` (2026-07-22, post-#981).**

## Objective

The single-source spec pattern wants the orchestrator to emit one line
(`task="implement {spec_path}"`) and have the executor read the full brief from the spec file. It
does not work today: **phase-1-init consumes the `description` verbatim and never reads a referenced
file**, so the one-liner ships an empty brief. Make the hand-off carry what it points at.

## ⚠ Mechanism — verified at `dfc4ac15c`

- `phase-1-init/SKILL.md:290-294` **Step 4 "Get Task Content"** — for a `description` input:
  "**Use description directly as original input / No additional context.**" A
  `task="implement {spec_path}"` string is recorded verbatim into `request.md`; the spec file at
  `{spec_path}` is **never opened**.
- The file-reading pre-flight that *would* ingest it is **lesson-only**, not a contract step, so it
  is advisory and skippable.
- **phase-2-refine merely existence-checks** the referenced paths (confirms they resolve), it does
  **not read** their content into the plan.

Net: the brief lives in the spec file; nothing in the init→refine path reads it; the plan proceeds
on a bare pointer. The more the pattern is trusted, the more silently briefs are lost.

## Deliverables

### D1 — GATE: trace where a referenced-file brief is (not) ingested (mutates nothing)

Confirm, against `main`, the exact init→refine path for a `description` that is a file pointer:
Step 4 verbatim-use, the lesson-only pre-flight, refine's existence-check. Decide the ingestion
seam — is it a new phase-1-init contract step (read `{spec_path}` into `request.md`), a refine step
(read into the plan brief), or both. Name the artifact each choice edits.

### D2 — promote file-ingestion from lesson to contract

Make phase-1-init (or refine, per D1) **read a referenced spec/brief file** when the input is a
pointer, folding its content into `request.md` / the plan brief so downstream phases see the brief,
not the pointer. Preserve the existing guard (SKILL.md:35): reading the brief is **recording
request material**, never a licence to implement in phase-1-init.

### D3 — make the failure loud, not silent

A pointer input that cannot be ingested (missing/unreadable spec file) must **error**, not proceed
on an empty brief — the same truthful-negative principle as PLAN-43. A one-liner that silently loses
its brief is the exact confident-signal-hides-a-caveat shape this epic is retiring.

### D4 — regression test: a pointer hand-off carries the brief

A test that runs init with `description="implement {spec_path}"` against a fixture spec and asserts
`request.md` contains the spec's content — not just the pointer string. Pins ingestion, not the
current verbatim-use.

## Expected surface

- `phase-1-init/SKILL.md` (Step 4 ingestion + the promoted pre-flight)
- possibly `phase-2-refine/**` (if D1 puts ingestion there)
- one new test under `test/plan-marshall/phase-1-init/**`

**Disjointness:** phase-1-init / refine surface — disjoint from `marshall-orchestrator` (PLAN-40,
shipped), `_markers_search.py` (PLAN-23), `manage-execution-manifest.py` (PLAN-35), the CI/await
seam (PLAN-42), `manage-architecture` (PLAN-43), and finalize steps (PLAN-44). Emittable now.

## Notes

- Without this, PLAN-40's D4 orchestrator half is a hand-off to a reader that discards it — the two
  halves are one capability split across a gate. This is the split completing, not new scope.
