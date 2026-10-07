# PLAN-51: compile-report Returns `success` While Silently Dropping Non-Empty Sections

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced by PLAN-23's (#986) retrospective — the **27th recurrence** of lesson
> `2026-06-20-17-003`. This run it **ate a real finding** (the pre-submission-self-review vacuous
> guard). Grounded @ `058a880c`. This is the epic's **flagship confident-signal-hides-a-caveat**
> archetype in the retrospective machinery itself.

## Objective

`plan-retrospective`'s `compile-report run` returns `status: success` even when `sections_omitted`
is **non-empty** — and an omitted section can carry a real finding. This run, `compile-report`
returned `sections_omitted: ['Phase Dispatch Boundaries']` and that dropped fragment carried a live
defect finding. Because the return is a clean `success`, the drop is invisible and the finding is
lost. It has recurred **27 times** and closed nothing. Make the drop loud.

## ⚠ Mechanism — verified at `058a880c`

- `plan-retrospective/scripts/compile-report.py:352` returns `'status': 'success'` with
  `:357 'sections_omitted': omitted` in the **same dict** — success is returned regardless of whether
  `omitted` is non-empty.
- `build_document` (`:261`) returns `(content, written, omitted)`; a fragment whose heading is not in
  `SECTION_SPEC` is appended to `omitted` (`:284`) and **not rendered**. The `:301` comment states it
  outright: the `SECTION_SPEC` loop "never looks them up and compile-report **silently** [drops
  them]."
- So the failure is two-layered, exactly the aspect-registry gap the operator named: (a) the
  **registry** (`SECTION_SPEC`) doesn't cover every emitted aspect, so real fragments fall through;
  (b) the **signal** reports `success` while they do.

## Deliverables

### D1 — GATE: trace the omit path and choose the loud-signal shape (mutates nothing)

Confirm how a non-empty `omitted` arises (heading absent from `SECTION_SPEC`) and every call site
that consumes `compile-report`'s `status`. Decide the signal: `status: warning` (the operator's
suggestion — "making it a warning would have made all five materializations loud") vs a distinct
non-success the retrospective flow must acknowledge. Decide whether the fix is signal-only (D2) or
signal **plus** registry completeness (D3) — the 27× recurrence argues both.

### D2 — non-empty `sections_omitted` is not a clean success (the readable-signal half)

When `omitted` is non-empty, `compile-report` returns a **warning** (or the chosen loud status)
carrying the dropped headings, and the retrospective agent's contract treats a non-empty
`sections_omitted` as an item to surface — never swallowed under `success`. A dropped fragment that
carried a finding becomes visible at the point of drop.

### D3 — registry completeness so aspects don't fall through (the root half)

Give the dropped aspect(s) — starting with the observed `Phase Dispatch Boundaries` — a
`SECTION_SPEC` home, **or** add a catch-all "Other / unregistered aspects" render path so an emitted
fragment with an unknown heading is **rendered (appended), not vanished**. A real fragment must never
be silently unrenderable; at worst it lands in a clearly-labelled catch-all.

### D4 — regression test: an unregistered fragment is loud and not lost

A test that feeds `compile-report` a fragment with a heading absent from `SECTION_SPEC` and asserts:
(a) the return is a warning / non-clean-success naming the omitted heading (D2), and (b) the fragment
content is rendered (catch-all) or the registry covers it (D3) — never dropped under `success`. Pins
the invariant against the 28th recurrence.

## Expected surface

- `plan-retrospective/scripts/compile-report.py` (`build_document` omit path + the run return status)
- `plan-retrospective/SKILL.md` (the retrospective agent's contract on `sections_omitted`)
- `SECTION_SPEC` / the aspect registry (D3)
- a test under `test/plan-marshall/plan-retrospective/**`

**Disjointness:** `plan-retrospective` surface — disjoint from every other truthful-signals plan and
from plan-optimization's running PLAN-35. Emittable now.

## Notes

- Flagship archetype instance (7): a tool returns `success` while suppressing the caveat
  (`sections_omitted` non-empty) that makes the answer wrong — same shape as the false-green build
  (#979), PLAN-42 (waiting fallback), PLAN-43 (architecture-find), PLAN-46 (title non-delivery).
- **27× recurrence with zero closure** is itself a signal about the lessons pipeline (retrospective
  found the defect five times, filed a lesson each time, changed nothing) — noted as the separate
  "lessons-pipeline records-but-closes-nothing" candidate, not scoped here.
- The `:301` code comment already documents the silent drop — a **doc-contract-divergence** flavour:
  the code admits the bug in a comment while the return says `success`.

## Lessons Carried (bound 2026-07-25 · lessons-triage)

The plan lifecycle MUST carry the lesson(s) below so each lives/moves with the plan and leaves the
global corpus when the fix lands: at phase-1-init run
`manage-lessons convert-to-plan --lesson-id {id} --plan-id {plan_marshall_plan_id}` (relocates the
lesson into this plan's directory); the finalize `lessons-housekeeping` step then retires it (this
plan's fix supersedes it — provenance goes to the tombstone `--reason`, never a lesson-id citation).

- `2026-06-20-17-003` — chat-history-analysis aspect dead (missing `SECTION_SPEC` row); the exact
  defect this plan closes, and its 27× recurrence is this plan's raison d'être.
