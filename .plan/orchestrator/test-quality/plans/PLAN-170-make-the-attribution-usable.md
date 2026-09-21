# PLAN-170: Make the Attribution Usable — Stop Reading a Lead as a Claim

epic: test-quality
workstream: WS-06

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator at PLAN-120's landing**, from the one result PLAN-120 was
> commissioned to produce and could not: a per-slice budget attribution a campaign run can be
> sized from. PLAN-120 shipped the derivation correctly and the derivation returned a single
> bucket. This plan makes the answer usable. It is PLAN-120's direct successor and touches the
> same skill.

## Objective

The epic commissioned two derived sets. One works: the partition classifies 21 specs into
19 declarative / 1 derived / 1 prose, and the whole-tree budget population it reports (**279** at
HEAD `00b92fca`) is confirmed exactly by two independent methods. The other is unusable:

```text
partition:   claimed 2 | unclaimed 0 | multiply_claimed 1057 | not_derivable 0   (of 1059)
attribution: buckets[1] — <multiply-claimed>, 279
```

**All 279 budget findings land in one bucket, so nothing is attributed to any owner.** The cause
is **seven whole-tree `test/` root claims** parsed from five specs — and five of the seven are not
ownership claims at all. Make the derivation distinguish a claim from a lead, and give the
attribution a way to report a slice owner in the presence of a plan that deliberately sweeps
everything.

## Deliverables

1. **D1 — Stop resolving a `HYPOTHESIS: … (verify-at-outline)` entry into a declarative claim.**
   ⛔ **Gating, and the whole cause of the collapse.** PLAN-120's D1 classifies **per spec**
   (declarative / derived / prose) but resolves **per entry**, so a spec classified `declarative`
   overall has every one of its entries resolved as declarative — including entries the epic's own
   convention marks as leads. Verified per instance, and the result is unanimous:

   | Spec | Root claim | The entry it came from | Verdict |
   |---|---|---|---|
   | PLAN-105 | `test/` | `HYPOTHESIS: ~391 files across test/ and marketplace/bundles/ — D7's final sweep (verify-at-outline)` | **lead** |
   | PLAN-120 | `test/` | `OBSERVED: that script's tests, under test/` — a *collection constraint* (`testpaths`), not a claim | **not a claim** |
   | PLAN-160 | `test/**` ×3 | three `HYPOTHESIS: … across test/** — R1's / R3's / R4's output (verify-at-outline)` rows | **leads** |
   | PLAN-130 | `test/` | "this plan crosses the whole partition by construction" | **genuine claim** |
   | PLAN-135 | `test/` | stated identically | **genuine claim** |

   ⛔ **This is the same defect class PLAN-120 already fixed once inside its own run.** Its
   `_raw_mentions_module` bug read an unresolved span as a resolved one and manufactured
   `unclaimed` verdicts out of the parser's limits; this reads a *lead* as a *claim* and
   manufactures `multiply_claimed` verdicts the same way. The tool already has the right verdict
   for it — `not_derivable` — and these entries bypass it.
   *Done when:* entry-level shape is classified independently of spec-level class; a
   `HYPOTHESIS:`/`verify-at-outline` entry resolves to `not_derivable`, never to a claim; the
   five rows above are reported as such by name; PLAN-130's and PLAN-135's survive as claims; and
   a matched negative control shows the old behaviour failing the new tests.

2. **D2 — Give the attribution a sweep-plan concept, so a whole-tree claim stops erasing slice
   ownership.** After D1 the two genuine whole-tree claims (PLAN-130, PLAN-135) still cover every
   module, so every module is still multiply-claimed and the attribution still returns one bucket.
   A plan that sweeps the tree by construction is **not** competing for ownership with the slice
   plan that owns a directory — it is orthogonal to it.
   ⛔ **Do not resolve this by dropping sweep plans from the partition.** Their coverage is real
   and a reader must still be able to ask "who touches this module?" Report both: the **owning
   slice** and the **sweeps that also cross it**, as separate facts.
   *Done when:* the attribution reports a named owner per finding for every module a slice plan
   claims; the sweep plans are reported alongside rather than merged in; and the residual
   genuinely-contested set (a module two *slice* plans both claim) is reported separately and is
   **small enough to enumerate**.

3. **D3 — Validate against the baseline the epic has been unable to reproduce.** With D1 and D2 in
   place, re-derive the per-slice attribution and compare against the epic's recorded slice figures
   (030:40, 040:57, 050:3, 060:55, 070:62, 080:49, +1 for PLAN-010's rule-test glob, against a
   then-population of 267).
   ⚠️ **The population has moved four times and will move again** — 267 (`2cd1a19c`) → 270
   (`77db1a0d`) → 271 (mid-flight) → **279** (`00b92fca`). **Do not treat a non-match as failure**:
   re-derive the whole-tree total first, attribute the delta per instance, and only then compare
   shapes. A slice whose count moved by exactly its attributable additions is a **match**.
   *Done when:* the whole-tree total is re-derived and stated with its command; every slice figure
   is reported with its delta attributed per instance; and any slice that does not reconcile is
   named with the modules that explain it.

4. **D4 — Report.** The seven root claims before and after; the per-entry classification for every
   spec; the attribution before (one bucket) and after; the D3 reconciliation; and the residual
   contested set enumerated.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: the attribution returns `buckets[1]{owner,count}: <multiply-claimed>,279` and the
  partition returns `claimed 2 | unclaimed 0 | multiply_claimed 1057 | not_derivable 0` of 1059
  modules — re-derived by the orchestrator at HEAD `00b92fca` by running the landed tool directly
- OBSERVED: the whole-tree `test-module-line-budget` population is **279** at HEAD `00b92fca`,
  confirmed by three independent methods that agree exactly — the doctor's `rules_run` tally, a
  `git ls-tree` + `wc -l` sweep, and the landed tool's own `attribution`
- OBSERVED: `root_claims[7]` names PLAN-105 (`test/`), PLAN-120 (`test/`), PLAN-130 (`test/`),
  PLAN-135 (`test/`) and PLAN-160 (`test/**` three times)
- OBSERVED: five of the seven trace to a `HYPOTHESIS:`/`verify-at-outline` entry or a collection
  constraint — verified by reading each spec's `## Expected Surface` per instance, listed in D1
- OBSERVED: PLAN-130's and PLAN-135's whole-tree claims are deliberate and stated in both specs as
  "this plan crosses the whole partition by construction"
- HYPOTHESIS — **gating for D2; the count is a lead, not a target**: after D1 the residual
  genuinely-contested set is small enough to enumerate. Confirm/refute by re-running the partition
  with D1 in place before scoping D2 (verify-at-outline)
- OBSERVED — **an asserted absence, verify it**: PLAN-120's spec is history and is **not** edited by
  this plan. Its `test/` root claim is corrected by narrowing the *parser's* reading, never by
  editing a shipped spec

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_spec_parser.py` — D1
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py` — D2
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py` — D4's report sections
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/standards/epic-surface-derivation.md` — the entry-vs-spec class distinction is a contract change
- OBSERVED: `test/pm-plugin-development/tools-epic-surface-partition/` — the tests, inside PLAN-080's existing recursive claim
- OBSERVED: this plan **edits no spec under `plans/`** and **modifies no existing test module outside its own skill's mirror**

## Dependencies and Sequencing

- Depends on: **PLAN-120 (landed, #1345)** — this plan edits the skill it shipped.
- ⛔ **Land it before PLAN-140's next campaign run.** PLAN-140 is sized from the per-slice
  attribution, and that attribution currently returns one bucket. Running the campaign before this
  lands means sizing it by hand again — the manual pass PLAN-120 was commissioned to remove.
- Overlaps with: **PLAN-105 / PLAN-145 / PLAN-165** on `marketplace/bundles/**`, LIVE — the
  derivation reports 18 live overlapping entries across PLAN-010 / 090 / 105 / 145 / 165.
  ⚠️ The overlap is confined to this skill's own directory, which no other staged plan claims, so
  a **file-level** check is what governs the pairing decision, not the tree-level one.
- ⛔ **PLAN-160 carries no `marketplace/bundles/**` claim at all** — the epic's outline predicted
  one and the derivation refuted it. Do not re-inherit the outline's prediction.

## Out of Scope

- **Editing any spec under `plans/` to resolve a disagreement.** PLAN-120's Out of Scope named this
  "the single most available wrong move", and it binds here with more force: this plan changes the
  checker, so moving the checked side too would leave no independent verdict at all.
- **Editing PLAN-120's shipped spec.** Its root claim is a parser-reading defect, not a spec defect.
- **Flipping any doctor rule from `warning` to `error`.** That decision now has three instances
  behind it and belongs to WS-03, not here.
- **Any `test/` refactoring** and **any change to the doctor's rules or output format**.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-170-make-the-attribution-usable.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
