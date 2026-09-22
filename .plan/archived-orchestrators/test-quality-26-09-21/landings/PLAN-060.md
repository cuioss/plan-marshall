# Landing Analysis: PLAN-060 — Runtime and Script Substrate Test Reduction

epic: test-quality
workstream: WS-02
pr: #1263 (run 01), #1265 (run 02), #1272 (run 03)

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf. Three runs; the latest report's
> residue is authoritative.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — hoist repeated `monkeypatch` isolation into function-scoped, explicitly-requested fixtures (**B4**) | **shipped-as-specified** | Ratio reported 17.70:1 → 6.38:1. Re-derived at HEAD: (433 `setattr` + 139 `setenv`) : 87 fixtures = **6.57:1**, consistent, with the delta explained by 13 ordinary unrelated commits |
| D2 — split every module over the 400-line budget | **not done across all three runs, correctly reported** | **55** over budget at HEAD (report: 53). The report's bound is confirmed: `TestInstallTerminalTitleHooks` at `test_claude_runtime.py:482` is a **663-line class** that exceeds the budget alone, so a class-boundary split cannot reach it |
| D3 — **B6** `parse_ns` everywhere reachable; **B7** no `spec_from_file_location` | **shipped-substantially** | **B6**: 168 conversions, **184** `parse_ns` call sites at HEAD, ~39 raw `Namespace(` remaining against 29 AST-derived documented exceptions — same order, differing methodology. **B7**: 17 → 2 reported; **3** remain at HEAD, of which two are synthetic fixture strings representing generated code under test, not real preambles |
| D4 — **B5** parametrize tabular families; **B3** strip historical prose to zero findings | ⛔ **REFUTED at HEAD** | Running the doctor per-directory across all 14 sums to **14** `test-docstring-historical-prose` findings (`script-shared` 3, `tools-script-executor` 7, and four more) — all bare `deliverable N` without the `D` prefix. Same root cause as PLAN-050: **PLAN-090's later matcher widening made the `D` prefix optional**, exposing pre-existing citations this plan recorded and declined to fix because the rule could not then see them. **B5** independently confirmed still at 1 of ~224 families |
| D5 — derive the property-based-testing candidate list, add no dependency | **shipped-as-specified** | 38 candidates. `grep -in hypothesis pyproject.toml` → **0**; the three tree-wide `hypothesis` hits are incidental and unchanged. The dependency was correctly not added |
| D6 — report the measured deltas | **unverifiable** | Collected-count, coverage and wall-clock figures need a build |

## Metrics and Anomalies

- The retired percentage line floor: **0.72%** against a **25%** floor — a floor exceeding the slice's
  entire prose volume, in a slice whose mean test is already 11.7 lines, **inside B2**.
- ⚠️ **Anomaly worth preserving — run 01 found a live order-dependent hermeticity failure (F10) using
  nothing but reverse directory order.** Run 03 fixed it, plus six new `sys.modules` collisions that
  run 01 and 02's **own** preamble conversions had introduced (F11). The conversions were correct and
  still created the collisions; that is the risk PLAN-105 § D7 and PLAN-140 both inherit.
- The randomised hermeticity arm went **unrun across all three runs** — `pytest-randomly` is absent and
  adding it is a user-approval step.

## Routing and Merge Behavior

- Review: run 03 closed F10 and F11, both self-inflicted or self-discovered rather than reviewer-raised.
- CI/merge: all three runs landed.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `pr` stamped → `#1263, #1265, #1272`
- [x] row `landing` stamped → `landings/PLAN-060.md`
- [x] Open Defect opened — the **B3** prose-regression class (shared with PLAN-050)
- [x] Open Defect opened — D4's 223 parametrization families have **no owner anywhere**
- [x] Open Defect opened — `test_extension_discovery.py:458` never converted after the accessor shipped

## Follow-Ups

- ⛔ **The prose regression is the second instance of a systemic class, confirming it is not a one-off.**
  PLAN-090's widening was correct; nothing swept `test/` afterwards. Staged as **PLAN-130**.
- ⛔ **D4's parametrization deliverable is the largest genuinely-open item in the epic with no owner at
  all** — ~223 families at ≥80% skeleton similarity, ~4,554 lines, each needing a **read** because the
  set includes `script-shared`'s deliberate matched control pairs that must **not** collapse. It appears
  in neither the README's "now owned elsewhere" column nor the collision matrix. **D4's required cold
  read was also never performed, across all three runs.** Staged as **PLAN-150**.
- ⛔ **PLAN-090 shipped `conftest.load_skill_module` for exactly the bundle-root `extension.py` shape
  this plan's report-03 named as blocking (H6) — and this slice's own call site was never converted.**
  `test/plan-marshall/extension-api/test_extension_discovery.py:458` still uses raw
  `spec_from_file_location`, while the equivalent site in PLAN-080's slice **was** converted. A fix
  shipped and one of its two known consumers never adopted it. Folded into **PLAN-130**.
- **D2's 55 over-budget modules** are the campaign's, with the stated bound that exactly one class
  exceeds the budget alone. **Three latent `sys.modules` registrations** with no plain importer today
  were routed to PLAN-090 § D3 and are not covered there. Both recorded in the epic's `## Open Defects`.
