# Landing Analysis: PLAN-070 — Architecture and Orchestration Test Reduction

epic: test-quality
workstream: WS-02
pr: merged at `6514cf24`

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — rename `build_test_helpers.py` → `_build_extension_fixtures.py` and `discovery_test_helpers.py` → `_discovery_fixtures.py`; consolidate six `build-*` directories onto the shared fixture | **shipped-as-specified** | Both new names present; both old names absent from the tree |
| D2 — build one plan-lifecycle staging fixture on `plan_context`, **if** the nine phase/lifecycle directories do not already share staging | **correctly not built — the gating hypothesis was refuted** | The report's own table shows 4 of 15 modules across 3 of 9 directories already share `plan_context`, and no module stages inline in 3+ tests: the done-when **already held on main**. The plan explicitly instructed "say so rather than building a second", and the run did |
| D3 — **B7** eliminate `spec_from_file_location` and deep parent chains | **shipped-as-specified with a stated exception list** | Re-derived exactly: **10 sites across 9 modules**, unchanged since landing. Seven are PLAN-090 § D2's shape (skill-root `extension.py` / repo-root `build.py`), one needs `050`/`090` coordination, one is by design in `_build_extension_fixtures.py:139` |
| D3 — **B6** convert `Namespace(` sites to `parse_ns` | ⛔ **not done — 0 conversions** | **1** `parse_ns` call in the whole slice, unchanged. **518** raw `Namespace(` at HEAD (report: 506), minus 12 `SimpleNamespace` = **506 hand-built** (README says 494 against the report's population). **This is the epic's single largest remaining B6 surface**, and no follow-up run has been dispatched — the plan directory holds only `report-01.md` |
| D4 — **B3** strip historical-prose citations | **shipped against the rule-scoped done-when; residue disclosed** | The report claims 42 → 0 doctor findings and explicitly flags ~20 residual citations in shapes the rule cannot match (string literals, bare `TASK-n`, bare `D2`). Not re-run here; qualitatively consistent |
| D4 — **B5** parametrize the tabular families | **partially not needed, partially open** | The build-detection matrices had already converged on `main` pre-run. The architecture query-filter and inbox-envelope families are **untouched** |
| D5 — report the measured deltas | **shipped-as-specified** | Every required figure present with its command, internally reconciled across three verification rounds (F20–F28 corrected the report's own figures) |

## Metrics and Anomalies

- Slice: 65,163 lines / 171 modules at the branch point → **66,338 / 173** at HEAD. Over budget: 62
  reported → **63** at HEAD (`test_determine_mode.py` crossed 400 via an unrelated commit).
- The retired percentage line floor: 20%, retired before this plan ran.
- **Anomaly — the report's own 506 figure is the raw grep.** It also matches the slice's 12
  `SimpleNamespace` uses. The seam map it measured is unaffected, so a follow-up run does **not** pay
  for the probe again. Recorded so the next run does not re-derive it.

## Routing and Merge Behavior

- Review: three verification rounds, F20–F28 of which corrected figures in the report itself.
- CI/merge: landed.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `landing` stamped → `landings/PLAN-070.md`
- [x] Open Defect opened — the ~500-site **B6** surface has no dispatched follow-up
- [x] Open Defect opened — two `ParserSeamNotFound` blockers routed to an owner that does not cover them

## Follow-Ups

- ⛔ **The epic's largest single remaining item.** ~506 hand-built namespaces against 1 `parse_ns` call,
  plus D4's two unconverted tabular families and ~20 rule-invisible citations. No follow-up run exists.
  Staged as **PLAN-150**.
- ⛔ **`090` was named as owner of two blockers it never touched.** `070`'s residue routes the
  `effort_presets.py` and `manage_terminal_title.py` `ParserSeamNotFound` blockers — and the three
  directories (`manage-lifecycle`, `build-server`, `q-gate-validation-agent`) that publish **no
  top-level CLI script at all**, a different shape — to PLAN-090 § D1. PLAN-090's own plan instructed a
  tree-wide `ParserSeamNotFound` re-derivation and its report **explicitly declined it** as *"not
  something this sweep replaces"*, scoping D1 to the 27 sites PLAN-060's plan had named. Neither module
  appears anywhere in `090`'s D1 discussion, and `effort_presets.py` still has no seam at HEAD.
  **Formally routed, actually unowned.** Folded into **PLAN-150**.
- **The 36 module/name pairs that patch an import-time binding of a doubly-registered module** —
  an AST-derived candidate order-dependency class with **only 1 confirmed live and fixed**. This is the
  same "rests on a single instance" shape as PLAN-090's R1/R3/R4. Recorded in the epic's `## Watches`.
- **Declined, correctly, and still declined:** `CANONICAL_SUBDIRS`
  (`build-pyproject/test_dynamic_mypypath.py:21`) and `REAL_LESSON_IDS`
  (`plan-doctor/_doctor_fixtures.py:25`) are both still present and still hardcoded. A reviewer raised
  them; both are **pre-existing** and were declined with reasons on the threads. No action owed.
- **Closed since landing:** the stale `build_test_helpers.py` path in `conftest.py`'s docstring
  (routed to `090` § D6) is **fixed** — `grep` returns zero at HEAD.
