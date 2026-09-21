# PLAN-CIS-008 — ⛔ RETIRED 2026-08-08: SUPERSEDED IN FULL, DO NOT LAUNCH

epic: code-intelligence-substrate
workstream: WS-04
status: retired-superseded

> ⛔⛔ **THIS SPEC IS OBSOLETE. Every deliverable below has already shipped.** Retired at the 2026-08-08
> full-queue reconciliation and removed from the queue. The text is kept as the audit record; it is
> **not** a brief. **Do not emit a `/plan-marshall` command for it.**
>
> **Verified first-party against the implementing source, not inferred:**
>
> | Deliverable | Verdict | Evidence |
> |---|---|---|
> | D1 — add the missing `multi_module` rows | **SHIPPED** | `plan-retrospective/references/plan-efficiency.md:103-109` carries seven `multi_module` rows (`feature`, `bug_fix`, `tech_debt` anchored with explicit thresholds; the rest explicitly `fallback`). |
> | D2 — population-derived closure test | **SHIPPED, AND STRONGER THAN ASKED** | `test/plan-marshall/plan-retrospective/test_plan_efficiency_anchors.py` — `test_anchor_table_keys_are_exactly_the_live_cross_product` derives the axis from `SCOPE_ESTIMATE_VALUES` (`manage-solution-outline.py`) and asserts **exact cross-product equality**, not the ⊆ this spec asked for. It also carries the negative controls this epic demands: `test_cross_product_guard_fails_when_a_pair_is_removed` and `..._when_a_non_canonical_key_is_added`. |
> | D3 — distinguish the two fallback reasons | **SHIPPED structurally** | Every row is explicitly marked `anchored` or `fallback`, so an unanchored-but-valid combination is now a declared table state rather than a silent degradation. |
> | D4 — regression test | **SHIPPED** | Covered by the cross-product guard plus its two negative controls. |
>
> ⭐ **The vocabulary drift this spec was written against was resolved more thoroughly than the spec
> proposed**: the whole table was remapped onto the live five-value `SCOPE_ESTIMATE_VALUES`
> (`cross_cutting` → `multi_module`, `complex` → `broad`, `refactor` → `tech_debt`), and
> `plan-efficiency.md:78` records that eight of the previous table's twelve rows were **dead keys** —
> a larger gap than the one row this spec named. **The spec's own HYPOTHESIS ("the table contains
> exactly the four named rows") was correct when written and is now false.**
>
> ⛔ **THE LESSON THIS RETIREMENT CARRIES, and it is the reason to read this box rather than just
> delete the file:** this is the **SECOND** obsolete-spec finding of the same reconciliation — the first
> was `PLAN-CIS-015`'s D5 line, struck the same day for the same reason, and **both trace to the same
> lesson `2026-07-21-15-001`, whose "Closed sibling concern" section had recorded the closure all
> along.** ⇒ **A staged spec decays against a moving tree and NOTHING RE-GROUNDS IT.** Two plans were
> one emit away from re-shipping finished work. See lesson `2026-07-29-19-001` (*a staged spec premise
> EXPIRES; re-measure at outline, never inherit it*), folded into `PLAN-CIS-015` on the same day from
> an independent source — **three independent arrivals of one finding.**

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

`plan-retrospective`'s plan-efficiency aspect enforces absolute token/duration budgets from a
calibration-anchors table keyed by `scope_estimate`. The table has rows for exactly four values —
`surgical`, `single_module`, `cross_cutting`, `complex`. **`multi_module` is not one of them**, and
`phase-2-refine` sets `multi_module` whenever a change spans 2+ modules.

The result observed on PR #1056: the plan consumed **~2.37 M tokens (a floor) for a 10-file change**
and **no anchored budget check ever evaluated it**. The aspect fell back to four generic ratio
thresholds (three of which tripped), but the absolute budget — the thing that would have said "this is
too much for this change" — was never applicable, because there is no row to apply.

⛔ **The failure is silent by design.** The doc *specifies* a fallback for unanchored rows, so the
vocabulary gap reads as a supported path rather than as drift. A documented fallback is disguising a
missing gate.

## Deliverables

1. **Close the immediate gap** — add the missing `multi_module` rows (bug_fix / feature / refactor) to
   the calibration-anchors table so the value refine actually emits is anchored.
2. **Make the closure structural, not a one-time patch** — a population-derived test asserting
   `set(scope_estimate values the producers can emit) ⊆ set(rows in the anchors table)`. ⛔ **Derive
   the producer set from the producers** (`phase-2-refine` / `manage-status scope-estimate-heuristic`),
   never from a hand-written list, or this plan reproduces the archetype it is fixing.
3. **Distinguish the two fallback reasons** — the aspect emits an `error`-severity finding when it
   falls back for an **unrecognised** value, as opposed to a genuinely unanchored but valid
   combination. An unrecognised value is drift; an unanchored combination is a known hole. Today both
   render as the same graceful degradation.
4. **A regression test verified to FAIL pre-fix**, asserting that a plan carrying `multi_module`
   receives an anchored budget verdict rather than the generic-ratio fallback.

Four deliverables.

## Claim Labels

- **OBSERVED (orchestrator-verified at the landing)**: the run consumed ~2.37 M tokens for a 10-file
  change with no anchored budget applied; `references.json` recorded `scope_estimate: multi_module`,
  set deliberately at refine (`decision.log` `188867`: "Scope: multi_module - Modules: 3").
- **HYPOTHESIS (message-supplied, NOT orchestrator-verified)**: the anchors table contains exactly the
  four named rows and no `multi_module` row. Confirm/refute at
  `plan-retrospective/references/plan-efficiency.md` § the calibration-anchors table
  (verify-at-outline). **Do not scope until that table is read.**
- **HYPOTHESIS (derived)**: therefore *every* plan with `scope_estimate=multi_module` has run without
  an absolute budget anchor. The population is unmeasured — **D1 should measure it across the archived
  corpus rather than asserting it**, and report the affected count separately from the number of plans
  examined (volume-read-as-coverage is a recorded recurring archetype here).

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/plan-efficiency.md`
  — the calibration-anchors table (verify-at-outline).
- **HYPOTHESIS**: the producer side — `phase-2-refine` and `manage-status`'s scope-estimate heuristic —
  for the emittable-value set (verify-at-outline).
- **OBSERVED**: tests under `test/plan-marshall/plan-retrospective/**`.

**Disjointness:** `plan-retrospective` (references + aspect) and `manage-status` (read-only, for the
producer vocabulary). ⛔ **Same bundle as PLAN-CIS-012 and PLAN-CIS-013** — same serialization class, sequence,
never pair.

## Dependencies and Sequencing

- No hard dependency. Independent of PLAN-CIS-012's measurement-window work, though both touch
  `plan-retrospective` — sequence them.
- ⚠ If PLAN-CIS-012 lands first and changes how the aspect reports unavailable inputs, re-baseline D3
  against it, since "fell back" and "could not measure" may become the same reporting surface.

## Provenance

Staged 2026-07-29 from inbox message `inventory-blind-spot-010` (candidate-lesson) at the PLAN-01
landing. ⭐ Recorded because the irony is load-bearing, not decorative: **PLAN-01's own headline fix was
introducing `FILE_CATEGORIES` so an unknown category name becomes a distinguishable answer instead of a
confident empty one — and the retrospective auditing that plan hit the identical defect class in its
own budget gate.** Same archetype, one layer up: a consumer's hand-maintained lookup table is a subset
of a producer's enum, the miss path is a graceful degradation rather than an error, and the two drift
apart invisibly until the degradation becomes the normal path.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-008-scope-estimate-vocabulary-closure.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
