# PLAN-TRUTH-015: Rename marshall-orchestrator → plan-orchestrator (+ persona)

> Renamed from **PLAN-49** on 2026-07-30 (see `plan-id-rename-map.md`). ⭐ **This rename RESOLVES the
> legacy-carve-out collision** this plan's old id created: PLAN-49 sat inside
> `code-intelligence-substrate`'s former 1-49 block. The `TRUTH` scoping makes the collision
> structurally impossible, so the "renumber before it launches" problem is closed — by reissue, which is
> what a staged plan permits, not by a rename verb, which does not exist.

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Operator-requested 2026-07-22. ⚠ **DRAIN-GATED — RUNS LAST.** The operator will
> start this only when every other truthful-signals plan has landed (epic otherwise drained). It is
> **not** merely preference: this rename edits `orchestration-model.md`, `analyze.md`, `decompose.md`
> and **renames the directories** PLAN-47/48 (and the orchestrator surface generally) modify — running
> it before those land forces a 131-reference rebase and directory moves under in-flight plans.
> **NOT emittable until PLAN-41/42/43/44/45/46/47/48 have all shipped** (PLAN-27 is cross-epic and
> independent of this rename's surface — it does not gate this).

## Objective

Rename the two orchestrator skills across the whole repository, removing "marshall" from the
orchestrator surface:
- `marshall-orchestrator` → `plan-orchestrator` (the verb skill)
- `persona-marshall-orchestrator` → `persona-plan-orchestrator` (the persona)

## ⚠ Surface — SUPERSEDED by § Expected Surface below (re-derived at HEAD 2026-08-08). Retained as the `dfc4ac15c` reading only.

- **131 references** across **31 source-of-truth files** (72 `marshall-orchestrator` +
  59 `persona-marshall-orchestrator`).
- **3 directory renames:** `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/`,
  `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/`,
  `test/plan-marshall/marshall-orchestrator/`.
- **Cross-reference files:** `platform-runtime`, `manage-logging`, `manage-status`,
  `manage-terminal-title`.
- **Registration:** `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` +
  `marketplace/bundles/plan-marshall/README.md`.
- **Tests:** `test_orchestrator.py`, `test_orchestrator_archive.py`,
  `test_logging_orchestrator_store.py` (+ the test dir rename).
- **Docs (double-check — operator emphasis):** `doc/concepts/orchestration.adoc`, `README.adoc`,
  `planning-workflow.adoc`, `personas.adoc`.
- **Executor path:** `plan-marshall:marshall-orchestrator:orchestrator` →
  `plan-marshall:plan-orchestrator:orchestrator` (3rd part `orchestrator` unchanged); regenerated at
  finalize.

## Hard constraint

Rename ONLY the two orchestrator skills. Do **NOT** touch `marshall-steward`, `marshalld`,
`marshal.json`, or the `plan-marshall` bundle name — a naive global `marshall→plan` sed would corrupt
all of those. Match `marshall-orchestrator` / `persona-marshall-orchestrator` exactly.

## Deliverables

⚠ **Added 2026-08-08 — this spec had NO `## Deliverables` section**, only `## Acceptance`. It is the
hand-off brief, and `phase-1-init` ingests it as the request body, so a missing deliverable list left
the largest-surface plan in the queue with no stated units of work.

1. **D0 — GATE (mutates nothing): re-derive the surface at HEAD.** The spec's `dfc4ac15c` enumeration
   is superseded; the current reading is **210 matches across 54 unique files**. ⛔ Produce the file
   list, and **classify each hit as rename-target vs must-not-touch** — the `marshall-steward` /
   `marshalld` / `marshal.json` / `plan-marshall` exclusions are the whole risk of this plan.
2. **D1 — rename the two skill directories** and `test/plan-marshall/marshall-orchestrator/`.
3. **D2 — update every in-tree reference** to the two skills, including the 3-part script notation.
4. **D3 — update the cross-reference files** (`platform-runtime`, `manage-logging`, `manage-status`,
   and the rest of D0's list) and the 4 `doc/concepts/*.adoc` files.
5. **D4 — regenerate the executor** against the new 3-part paths.
6. **D5 — acceptance, each check verified**: zero remaining `marshall-orchestrator` /
   `persona-marshall-orchestrator` strings under `marketplace/`, `doc/`, `test/`, `plugin.json`,
   `README`; `plugin-doctor` clean; full test suite green. ⛔ **A grep returning zero is only meaningful
   with a matched positive control** — assert the sweep finds a deliberately-planted occurrence, or the
   zero is this epic's own vacuous-guard archetype.
7. **D6 — the `.plan/` ledger is NOT rewritten.** The orchestrator tree holds hundreds of references as
   **historical records**, not source. ⛔ State this as a non-goal and assert it, so nobody "completes"
   the rename by editing history.

Seven deliverables — well under the raised cap of 12. ⛔ **NOT merged with any other plan**: see
§ Dependencies and Sequencing — this is the exclusive plan, and merging anything into it would widen
an already-maximal blast radius.

## Acceptance

- Zero remaining `marshall-orchestrator` / `persona-marshall-orchestrator` strings in `marketplace/`,
  `doc/`, `test/`, `plugin.json`, `README` (grep-verified).
- Executor regenerated with the new 3-part path; `plugin-doctor` clean; all tests pass.
- The 4 `doc/concepts/*.adoc` files explicitly re-checked.
- Full PR flow.

## Emit note — ⛔ CORRECTED 2026-08-08, the previous instruction was STALE AND WRONG

The previous text said the hand-off *"MUST carry the full brief inline in `task=`, not as a
`task="implement {spec_path}"` pointer — phase-1-init does not yet read a referenced spec file
(that is PLAN-41, which ships before this)."*

**PLAN-41 SHIPPED as #991.** `phase-1-init` reads a referenced spec through the deterministic
`request create --body-file` seam, and `orchestrate.md` Step 5 now **mandates** the one-line pointer
and explicitly forbids reproducing spec text at the emit surface. ⇒ **The old instruction now
contradicts the live hand-off contract**, and following it would have re-introduced exactly the
retyping-drift that retirement removed.

**The hand-off is the ordinary one-line pointer** — see § Hand-Off Command below.

⭐ Recorded rather than silently deleted: this is a *precondition note that outlived its
precondition*. The plan it waited on shipped, and nothing re-read the note. Same shape as the stale
"BLOCKED" labels found on `PLAN-TRUTH-012` and `PLAN-TRUTH-005/006` in this same reconciliation.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-015-rename-marshall-orchestrator-to-plan-orchestrator.md"
```

## Expected Surface

- **OBSERVED, re-derived at HEAD 2026-08-08** (superseding the `dfc4ac15c` enumeration): the bare
  token `marshall-orchestrator` matches **210 lines across 54 unique inventoried files**;
  `persona-marshall-orchestrator` matches **76 lines across 29 files** and is a **subset** of the
  former (the string contains it), so 54 files is the surface, not 54+29.
- ⛔ **THE SPEC'S OWN FIGURE WAS 131 references across 31 files — THE SURFACE HAS GROWN ~74% IN
  FILES.** The spec said "re-verify at outline" and it was right to; do not scope on the old number.
- **OBSERVED**: 3 directory renames — `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/`,
  `.../persona-marshall-orchestrator/`, `test/plan-marshall/marshall-orchestrator/`.
- ⚠ **Coverage caveat**: `architecture search --content` is inventory-scoped, so `.plan/` (git-ignored)
  is NOT searched. That is correct here — the epic ledger's hundreds of references are **records, not
  source**, and must NOT be rewritten by the rename. State that explicitly at outline so nobody
  "completes" the rename by editing history.

## Dependencies and Sequencing

⛔⛔ **THIS IS AN EXCLUSIVE PLAN — it cannot run concurrently with anything touching the orchestrator
surface, and that is most of the queue.** Eleven staged plans reference `marshall-orchestrator` in
their expected surface: `-007 -008 -014 -022 -032 -033 -034 -036 -038 -050` and this one. A 54-file
rename landing mid-flight against any of them produces a rebase conflict in every one.

- **Run it ALONE.** `parallelization_scope` must effectively drop to 1 for its duration; do not pair
  it with any plan in the orchestrator cluster.
- **Sequence it LAST in that cluster**, not first. Rationale: every other orchestrator plan changes
  *behaviour* and is the reason the surface exists; this one changes only *names*. Renaming first
  forces ten specs to be re-grounded against new paths for zero behavioural gain; renaming last
  re-grounds one spec (this one) against a settled surface. ⭐ **A pure-rename plan should always be
  the last writer on its surface, never the first.**
- **Adjacent, deliberately untouched**: `marshall-steward`, `marshalld`, `marshal.json`, and the
  `plan-marshall` bundle name — see § Hard constraint. A naive `marshall→plan` sweep corrupts all four.

## Post-rename orchestrator transition

This session runs *as* `marshall-orchestrator`. After merge + executor regen + cache sync, the
orchestrator command path becomes `plan-marshall:plan-orchestrator:orchestrator`; the old path stops
resolving. The `.plan/local/orchestrator/` ledgers are not source (not renamed) — only their command
*strings* reference the old path and are updated in use post-merge.

## Notes

- Off the epic's truthful-signals theme — this is the epic's **closing refactor**, tracked here at
  operator request and gated on the epic draining. Emitting it is the last act before the epic's own
  archive decision.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
