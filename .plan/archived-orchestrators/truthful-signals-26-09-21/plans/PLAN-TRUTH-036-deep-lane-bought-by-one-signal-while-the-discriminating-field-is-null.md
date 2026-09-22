# PLAN-TRUTH-036: the deep lane is bought by ONE fired signal while the field that would have refuted it is null

epic: truthful-signals
workstream: WS-01

## Objective

`manage-status planning-lane route` selected `planning_lane=deep` for a plan whose realized footprint was
**9 files, +2,083 / −16**. The deep lane cost an estimated **~1.2M dispatched tokens (29% of the plan's
spend)**. The route decision, verbatim from
`.plan/local/archived-plans/2026-08-02-barrier-override-not-head-bound/logs/decision.log`:

```text
Routed planning_lane=deep (predicate=signal_set, fired=['S7:risk_prose'], ceremony.deep_lane=auto,
  execution_profile=standard,
  signals={'plan_source': None, 'scope_estimate': 'single_module', 'change_type': None,
           'compatibility': None, 'request_concrete': True, 'risk_prose': True,
           'planning_lane_override': None})
```

## ⭐ The root cause is sharper than "the sensor read rhetoric as risk"

⛔ **`plan_source: None`.** This plan WAS launched from an orchestrator plan spec — that is exactly what
`plan_source` exists to record, and `inbox detect` already classifies the pointer. **The one field that
identifies orchestrator-spec provenance, and could therefore have discounted the prose signal, was
null.**

And it is not alone: **three of the seven signals are `None`** (`plan_source`, `change_type`,
`compatibility`). The predicate is `signal_set` — deep if ANY member fires — so:

> **deep was bought on 1 fired signal out of 4 that resolved at all, against `scope_estimate:
> single_module` pointing the other way.**

⇒ ⛔ **Tuning the prose sensor is the WRONG fix and would leave the defect in place.** A `signal_set`
predicate over a mostly-null signal vector is **structurally biased toward firing**: every unresolved
field is a field that cannot vote against.

## ⛔⛔ Self-implicating: this orchestrator's own authoring style is the trigger

`risk_prose: True` fired on a body that is an **epic plan spec written by this orchestrator**, in which
⛔ / ⚠ / ⭐ markup is a deliberate house convention for marking hard-won constraints — including in
`PLAN-TRUTH-034` and in this very document.

⇒ **Every plan this epic emits ingests such a spec.** The misfire is **structural, not occasional**, and
this orchestrator is its source. ⭐ **The sensor is measuring the author, not the change.**

⚠ **The tempting cheap fix — "the orchestrator should write plainer specs" — is rejected.** The markup
carries the anti-rework record that keeps plans from re-deriving settled constraints; degrading it to
placate a sensor trades a real good for a measurement artifact. **The sensor must learn provenance.**

## Deliverables

1. **D0 — GATE: derive why `plan_source` is null for an orchestrator-launched plan.** The pointer exists
   (`request.md` `source_id`) and `inbox detect` already classifies it. **Find the break: never
   populated, populated too late for the route, or populated under a different key.** ⛔ Answer this
   before touching any sensor — if the field simply arrives late, the fix is ordering, not scoring.
2. **D1 — make an unresolved signal visible in the decision.** Today `fired=['S7:risk_prose']` reads as
   a positive finding; it is equally a report that **three inputs were unknown**. The route record must
   state resolved-vs-null counts so a 1-of-4 decision cannot look like a 1-of-7 one.
3. **D2 — require corroboration for prose-only routing.** `S7:risk_prose` must not carry the lane alone
   when it **contradicts a resolved `scope_estimate`**, or when the body is a spec-pointer ingestion.
   ⛔ **Decide between corroboration and provenance-exemption and record the rejected one** — they are
   not the same fix and D0's answer should drive the choice.
4. **D3 — tests, each verified to FAIL pre-fix.** (a) Replay this exact signal vector → not `deep`.
   (b) An orchestrator-spec-sourced request resolves `plan_source` non-null. (c) A signal vector with
   ≥N nulls is reported as low-confidence. (d) ⛔ **A control assertion**: a genuinely deep-warranting
   vector still routes `deep` — **a fix that only ever de-escalates is a different defect**.

## Claim Labels

- **OBSERVED**: the route entry, verbatim, including all seven signal values.
- **OBSERVED**: `scope_estimate=single_module` classified at 20:47:17Z from `distinct_paths=7`,
  9 seconds before the route.
- **OBSERVED**: realized footprint 9 files, +2,083 / −16 (squash `967ba03f5`).
- **OBSERVED**: the ⛔/⚠ markup convention in this epic's own specs.
- ⚠ **REPORTED, NOT VERIFIED — the ~1.2M / 29% saving.** It comes from the originating finding, is not
  re-derivable from the artifacts cited in `PLAN-TRUTH-035` § Claim Labels, and depends on a per-step
  attribution that file does not contain. **Size it at D0; do not carry 700K–1.2M into a justification.**
- **HYPOTHESIS**: `plan_source` is null for *every* orchestrator-launched plan. **n=1 — DERIVE over the
  archived corpus at D0.** ⭐ If confirmed, the blast radius is every plan this epic has ever emitted,
  and that changes the priority, not just the description.
- **Verify-first clause**: D2 assumes `risk_prose` fires on the markup rather than on semantic content.
  **Confirm by reading the sensor's implementing source** — if it scores semantics, exempting
  spec-pointer bodies is the wrong lever.

## Expected Surface

- **OBSERVED**: `manage-status` — `planning-lane` route, the `signal_set` predicate, the `S7` sensor
- **HYPOTHESIS**: `phase-1-init` — where `plan_source` should be populated from `source_id`
- **HYPOTHESIS**: `marshall-orchestrator` — `inbox detect`, if D0 finds the classifier is the seam

## Dependencies and Sequencing

- ⛔ **SERIALIZATION PAIR with `PLAN-TRUTH-057`-class lane work** — `PLAN-57` (lane-router scale-blind
  false negative, shipped #1068) touched this router. **Re-ground against #1068 before scoping**: that
  fix addressed a false *negative*; this is a false *positive* at the same seam, and the two must not
  fight.
- ⚠ Adjacent to `PLAN-TRUTH-035` (both quantify the same run) but **surface-disjoint** — router vs
  metrics renderer. May pair if capacity allows.
- ⛔ Epic is **AT CAP (`parallelization_scope` = 1)**.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-036-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
and the sole sanctioned write mechanism are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⚠ FOLDED FROM THE 2026-08-09 (EVENING) DRAIN — WEAK MERGE, labelled as such

**`runtime-015` (finding).** *`get-module-context` can **never** succeed at phase-3 for a
`use_worktree=true` plan.*

⚠ **This is a WEAK merge and is licensed to be split back out at outline.** The tie is *phase-3 outline
machinery*, not a shared cause: this spec is about lane selection on a null discriminating field, and
this finding is about a context helper that is unreachable for a whole plan class. **They share a phase,
not a mechanism.**

⭐ Folded rather than staged because it is a single-site, falsifiable claim (*"can never succeed"*, not
*"sometimes fails"*) that would otherwise sit as an unowned lead — and this epic has watched unowned
leads rot. ⛔ **If outline finds the two deliverables do not compose, SPLIT IT BACK** rather than
widening this spec's blast radius to accommodate it.
