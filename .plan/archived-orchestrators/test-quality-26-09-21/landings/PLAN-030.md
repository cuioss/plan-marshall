# Landing Analysis: PLAN-030 — Config and Manifest Test Reduction

epic: test-quality
workstream: WS-02
pr: not recorded in the archived reports (two runs)

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — parametrize contract tables; no `test_*_includes_{knob}` family of 3+ near-identical functions remains | **shipped-as-specified** | `test_config_defaults.py` carries **6** functions across the two prefixes, no family of 3+ sharing one prefix. `test_decision_rules.py`'s largest name-shape group is 2 and it already carries 6 `parametrize` blocks. Run 02's F5 correctly identified that the "~100 remaining" figure was a **different, looser body-shape metric**, not the name-shape family the done-when targets |
| D2 — split every module over the 400-line budget | **not done, correctly handed off** | **40** modules over budget at HEAD (lead: 39). `test_config_defaults.py` at 3,703 lines and `test_manage_execution_manifest_compose.py` at 5,343 are still massively over. The operator re-scoped from the plan's 8-module lead to the real population and handed it to the campaign |
| D3 — arrange into fixtures/factories (**B4**), `parse_ns` conversion, exception list | **not started** | `monkeypatch.setattr` : `@pytest.fixture` = **259 : 13**, a ratio of **19.9:1** — *worse* than the epic's ~11:1 corpus benchmark. **5** `parse_ns` sites, all pre-existing, none newly converted. The exception list is **empty by non-attempt**, which the plan's own report says plainly *"tells the operator nothing"* |
| D4 — one import preamble (**B7**) | **shipped-as-specified** | `grep` for `spec_from_file_location` and the deep `Path(__file__).parent…` chain over the slice returns **0**. Positive control: **86** files call `load_script_module` (run 02 stated 83) |
| D5 — docstrings state the invariant, not history (**B3**) | ⛔ **shipped-partial, claimed complete** | The rule-scoped half is genuinely clean — the doctor's `test-docstring-historical-prose` reports zero, and the single raw grep hit is a string-literal fixture filename, correctly exempt. **But D5's own deliverable text also requires stripping superseded-behaviour narration** (`used to`, `no longer`, `legacy`, `previously`), a class the rule's five citation-id patterns **cannot see**. The census command returns **245** hits in this slice. Sibling PLAN-040 performed exactly this reconciliation and reported its residue; **PLAN-030 never did, and declared D5 "Done" unqualified** |
| D6 — report the measured deltas | **shipped-as-specified** | All six figures present with commands across both runs; spot re-derivations reproduce modulo natural drift |

## Metrics and Anomalies

- Slice: 53,220 lines reported → **54,217** at HEAD (ordinary post-landing churn).
- The retired percentage line floor: **2.56%** achieved against a **30%** floor — a floor that demanded
  *more than the slice's entire prose volume*. Retired epic-wide.
- **Anomaly — a metric mismatch nearly became a false residue.** Run 01 reported "~100 families
  remaining" from a looser AST metric than the one D1's done-when names; run 02 caught it. This is the
  same *two ends measured two ways* class the campaign later formalised as its lesson 4.

## Routing and Merge Behavior

- Review: run 02's F7 — a reviewer-requested shared-registration mutable-state guard — was rejected as
  too narrow and routed to PLAN-090, **which did ship it** (`test_no_new_shared_registration_collision`
  in `script-shared/test_conftest_loader_contract.py`). A correctly-closed hand-off.
- CI/merge: both runs landed.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `landing` stamped → `landings/PLAN-030.md`
- [x] Open Defect opened — D5's unmeasured narrative half (245 census hits)
- [x] Open Defect opened — D3 unstarted with no owner

## Follow-Ups

- ⛔ **D5's "Done" is scoped to what the rule can see, and the deliverable was wider.** This is the
  **detection-versus-remediation** confusion that recurs across four plans in this epic: a clean rule
  count is not a clean slice when the rule's patterns are narrower than the deliverable's text.
  Staged as **PLAN-130**.
- **D3 has no owner.** The README lists it only as *"still open in its own slice"*, and no follow-up run
  is scheduled. Its `parse_ns` exception list being empty by non-attempt is explicitly **not** a clean
  result. Recorded in the epic's `## Open Defects`.
- **D2's 40 over-budget modules have a named owner (the campaign) that has not acted.** The campaign's
  run 1 took slice `050`; this slice is untouched. *Owner assigned* must not be read as *owner has
  acted* — recorded as a standing caution in the epic's `## Watches`.
- **The `subprocess-pythonpath` finding** in `marshall-steward/test_steward_determine_mode.py` (15
  findings tree-wide) remains unowned. Recorded in the epic's `## Open Defects`.
