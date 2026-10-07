# PLAN-150: Close the Architecture Slice's Namespace Conversion

epic: test-quality
workstream: WS-02

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator during epic ingestion**, from PLAN-070's own residue. That plan landed with
> its **B6** deliverable at **zero conversions** and no follow-up run was ever dispatched.

## Objective

`test/plan-marshall/`'s architecture and orchestration slice holds **506 hand-built `argparse.Namespace`
constructions against exactly one `parse_ns` call** — the epic's single largest remaining piece of work, and
the one **B6** conversion still to come. A hand-built namespace does not carry the parser's defaults, so a
test can pass against a namespace the real CLI would never produce, and a newly-added flag with a default
breaks nothing in the suite while breaking production. That is a correctness defect, not bloat. PLAN-080's
slice is the precedent — 211 sites converted to zero, with **all 39** resulting `parse_ns` calls hoisted to
module scope so the conversion paid no per-call cost. This slice is roughly **2.3× that size**.

## Deliverables

1. **D1 — Re-derive the population and the seam map.** ⛔ **Gating.** Derive the slice's hand-built namespace
   count, its `parse_ns` count, and for every target script whether a seam exists.
   ⚠️ **Subtract `SimpleNamespace` before reporting.** PLAN-070's report states 506 as the raw
   `grep 'Namespace('`, which also matches the slice's 12 `SimpleNamespace(` uses — a different construct
   that **B6** does not govern. The epic's own brief carries the corrected arithmetic; getting this backwards
   inflates the target by 12 and misreports the outcome.
   ⚠️ **The seam map PLAN-070 measured does not need re-measuring from scratch** — its blockers are recorded
   and PLAN-145 is what resolves them. Re-derive the *count*, reuse the *map*, and say which you did.
   *Done when:* the hand-built count, the `SimpleNamespace` count, the `parse_ns` count and the per-script
   seam verdict are each recorded with their commands, and the set blocked by a missing seam is named.

2. **D2 — Convert, hoisting every call to module scope.** Replace each hand-built namespace with `parse_ns`
   against the script's own parser.
   ⛔ **Hoist.** `parse_ns` re-executes the script module on every call — its own docstring says so — and a
   test building many namespaces must lift the call into a fixture or a module-level constant rather than
   calling it per assertion. PLAN-080 got **39 of 39** to module scope; this slice is 2.3× larger, so the
   cost of not hoisting is 2.3× worse.
   ⛔ **A site blocked by a missing seam is left and named, never worked around** with a hand-built namespace
   carrying a comment. PLAN-145 owns those; if it has not landed, this run reports the blocked set and
   converts the rest.
   *Done when:* the hand-built count is reported before and after; every `parse_ns` call is at module or
   fixture scope, with any exception named; every blocked site is listed with the script that blocks it; and
   the affected directories pass in **default and reverse** order.

3. **D3 — Close the two remaining tabular families.** PLAN-070's **B5** half converged the build-detection
   matrices before its run started, and left two families untouched: the **architecture query-filter** cases
   and the **inbox-envelope** cases.
   ⛔ **Two tests differing only in input and expected output are one `parametrize` with an `ids=` list
   carrying what the two docstrings said** — the `ids=` is not optional, it is where the removed prose goes.
   ⚠️ **A matched positive/negative control pair is not a tabular family and must not collapse.** Read before
   collapsing.
   *Done when:* both families are parametrized or each is named with why it is not a family; the collected
   item count is **unchanged or higher**; and no control pair has been merged.

4. **D4 — Report the measured deltas.** The **B6** counts before and after with `SimpleNamespace` stated
   separately; the hoist audit (every call site and its scope); the blocked set; the two families' outcome;
   the collected item count before and after; the skipped count; and the wall-clock with its population named.
   ⚠️ **Report the ~20 rule-invisible **B3** citations PLAN-070 disclosed** — do **not** fix them. PLAN-130
   owns that sweep tree-wide, and two plans editing the same docstrings is the collision this epic exists to
   avoid.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: the slice carries **1** `parse_ns` call and **560** raw `Namespace(` at HEAD `09f92b5e`, of
  which **13** are `SimpleNamespace`, giving **547** hand-built. ⛔ **Re-scoped from 518 / 12 / 506**, which
  held unmoved across three shas (`3bc01075`, `77db1a0d`, `00b92fca`) and has now moved by **+42** in one
  window. Re-derive before executing: the conversion target is larger than the spec was sized against,
  while `parse_ns` is unmoved at 1
  - verdict: contradicted | checked_at: 09f92b5e | by: test-quality/cleanup | rescoped: yes | evidence: refuted and RE-SCOPED IN PLACE at HEAD 09f92b5e: re-derived over the full 070 slice directory set - raw Namespace( 560 (was 518), SimpleNamespace 13 (was 12), hand-built 547 (was 506), parse_ns 1 (unmoved). The prior stamp established 518/12/506/1 as reproducible across THREE shas (3bc01075, 77db1a0d, 00b92fca); it has now moved +42 in a single window, so the stability that justified trusting it is gone. The conversion target is 8 percent larger than the spec was sized against
- OBSERVED: PLAN-070's report states **506** raw where the epic brief states **494** hand-built. The
  difference is exactly the 12 `SimpleNamespace` uses; **the seam map it measured is unaffected**, so a
  follow-up run does not pay for the probe again
- OBSERVED: no follow-up run of PLAN-070 was ever dispatched — its archived directory holds `plan.md` and
  `report-01.md` and nothing else
- OBSERVED — **the precedent, and it is favourable**: PLAN-080's slice went from ~211 hand-built and zero
  `parse_ns` to **zero** hand-built and **39** `parse_ns`, **every one at module scope**. A full-slice **B6**
  conversion need not pay the per-call cost
- OBSERVED: `parse_ns` re-executes the script module on every call — read at `test/conftest.py` § `parse_ns`
  docstring
- HYPOTHESIS — **and PLAN-145 is what settles it**: two named scripts (`effort_presets.py`,
  `manage_terminal_title.py`) and three directories publishing no CLI script at all block some share of the
  506 — confirm/refute at D1's seam map (verify-at-outline). ⛔ **The blocked count is unknown**, because no
  run has ever derived it tree-wide; sizing this plan without it is what PLAN-070 did
- OBSERVED: **10** `spec_from_file_location` sites across 9 modules remain in this slice, unchanged since
  landing. ⛔ **Not this plan's** — PLAN-135 owns the preamble sweep tree-wide

## Expected Surface

⚠️ **This is PLAN-070's slice, enumerated so the disjointness check can resolve it. Re-derive it from
PLAN-070's own spec at outline** rather than trusting the transcription.

- OBSERVED: `test/plan-marshall/build-gradle/`
- OBSERVED: `test/plan-marshall/build-maven/`
- OBSERVED: `test/plan-marshall/build-npm/`
- OBSERVED: `test/plan-marshall/build-operations/`
- OBSERVED: `test/plan-marshall/build-pyproject/`
- OBSERVED: `test/plan-marshall/build-server/`
- OBSERVED: `test/plan-marshall/execute-task/`
- OBSERVED: `test/plan-marshall/manage-architecture/`
- OBSERVED: `test/plan-marshall/manage-lifecycle/`
- OBSERVED: `test/plan-marshall/manage-personas/`
- OBSERVED: `test/plan-marshall/manage-plan-documents/`
- OBSERVED: `test/plan-marshall/manage-terminal-title/`
- OBSERVED: `test/plan-marshall/phase-1-init/`
- OBSERVED: `test/plan-marshall/phase-2-refine/`
- OBSERVED: `test/plan-marshall/phase-3-outline/`
- OBSERVED: `test/plan-marshall/phase-4-plan/`
- OBSERVED: `test/plan-marshall/plan-doctor/`
- OBSERVED: `test/plan-marshall/plan-marshall/`
- OBSERVED: `test/plan-marshall/plan-orchestrator/`
- OBSERVED: `test/plan-marshall/finalize-step-plugin-doctor/`
- OBSERVED: `test/plan-marshall/finalize-step-preference-emitter/`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/`
- OBSERVED: `test/plan-marshall/finalize-step-sync-baseline/`
- OBSERVED: `test/plan-marshall/finalize-step-sync-plugin-cache/`
- OBSERVED: `test/plan-marshall/q-gate-validation-agent/`
- OBSERVED: `test/plan-marshall/ref-workflow-architecture/`
- OBSERVED: `test/plan-marshall/targets-claude/`
- OBSERVED: `test/plan-marshall/test_lane_refactor_cleanup_sweep.py`
- OBSERVED: `test/plan-marshall/test_plan_marshall_plugin_extension.py`
- OBSERVED: **no `marketplace/bundles/**` file.** A missing seam is **recorded**, not fixed here — though
  PLAN-145's D1 established the blocked set is **empty**, so this is now a defensive note, not a live route
- OBSERVED: **no docstring rewrite for B3.** PLAN-130 owns that sweep

## Dependencies and Sequencing

- ✅ **NO LONGER DEPENDS ON PLAN-145 — the dependency is RETIRED, and this plan is unblocked.** It formerly
  read "depends on PLAN-145, which publishes the seams this conversion needs; it cannot finish without it."
  PLAN-145's own D1 refuted that at outline and filed the result through the epic inbox: of **118**
  entry-point scripts under `marketplace/bundles/`, **113** already reach a parser seam and the **5** that
  raise `ParserSeamNotFound` are all deliberate shapes (a dispatch router whose raise is pinned as intended
  contract by a passing test, three stdin-driven hooks, one import-only library). **Modules owed a
  `build_parser()` seam: 0. `parse_ns` sites this plan is blocked on: 0.** The D4 figure this plan was to
  be sized from is `0`. Corroborated independently at HEAD `09f92b5e`. ⛔ **Do not re-inherit the retired
  dependency** — it came from PLAN-070's report routing "no seam" and "no CLI" to the same remedy.
- Depends on: PLAN-010, PLAN-020, PLAN-090 — all landed.
- ⛔ **Must not run concurrently with**: PLAN-140 run 5 (the same slice — the sharpest collision in the
  epic), PLAN-130 or PLAN-135 (both sweep every slice), PLAN-110 (`build-server/` is in this slice, and
  PLAN-110 records a platform exception there).
- **May run concurrently with**: PLAN-155 (PLAN-060's slice, disjoint from this one), PLAN-120, and
  PLAN-145's production half — ⚠️ **subject to PLAN-145's own tests landing under
  `test/plan-marshall/{skill}/`, several of which are inside this slice.** Confirm the specific directories
  before pairing.

## Scope Note

⚠️ **506 sites is large for one run.** The epic's own evidence is that a run completes two to three code
deliverables, and this plan has four with D2 carrying almost all the weight. **Convert by directory and
commit per directory**, so a run that exhausts its budget lands what it did rather than losing it — and
**report what was not reached rather than thinning what was**. A second run against this spec is expected
and is not a failure.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-150-close-the-architecture-slice-namespace-conversion.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
