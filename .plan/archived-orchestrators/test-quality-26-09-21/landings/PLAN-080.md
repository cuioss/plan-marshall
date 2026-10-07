# Landing Analysis: PLAN-080 — Plugin Development and Generator Test Reduction

epic: test-quality
workstream: WS-02
pr: #1306 (run 02); run 01 PR not recorded

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf. Two runs.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — rename `_fixtures.py` → `_plugin_doctor_fixtures.py`; convert `test_analyze_*.py` onto the `assert_analyzer_findings` scaffold | **shipped-as-specified** | New name present, old absent. **51** modules import the scaffold. The 6 unconverted modules are exactly the ones the report names and characterises, none convertible without changing what the test asserts |
| D2 — preserve the suite-coverage meta-test through every D1 move; `EXEMPT_RULE_IDS` must not grow | **unverifiable** | Requires running the doctor's meta-test. The report's own evidence — `git diff -M` showing **zero** content lines on the rename commit — is structurally sound and was independently confirmed by run 01's verifier |
| D3 — **B7** eliminate `spec_from_file_location` | **shipped-as-specified to its structural floor** | 59 → 9 (run 01) → **2** (run 02). The floor is `generate.py` and the repository-root `build.py`, both **outside** `marketplace/bundles` and therefore unreachable by `load_skill_module`. Confirmed at HEAD |
| D3 — **B6** convert `Namespace(` to `parse_ns` | **shipped-as-specified at landing; REFUTED at HEAD by drift** | The claim "**211 of 211**, 0 hand-built, 39 `parse_ns` all at module scope" was **true when written**. At HEAD, `tools-corpus-language-server/test_corpus_lsp_honesty.py:500` carries a genuine hand-built `argparse.Namespace(...)` call. That file was added **2026-08-21 by PR #1321**, an unrelated code-intelligence epic, *after* run 02 landed |
| D4 — derive the property-based-testing candidate list for the generator half | **shipped-as-specified** | 9 candidates / 7 modules / 47 example rows, including a **self-corrected error** (a pair wrongly called a round-trip). The correction is itself evidence of the report's verification discipline working |
| D5 — report the measured deltas | **shipped-as-specified** | Both reports carry every required figure with commands. ⚠️ **Run 02's coverage gap is explicitly disclosed, not silently omitted** |

## Metrics and Anomalies

- Slice: 60,667 lines / 162 modules reported → **67,416 / 168** at HEAD (+6,749 lines). Over budget:
  42 reported → **49** at HEAD (+7).
- ⛔ **Anomaly — this landing has already been overtaken by drift, within one to two days.** Two
  unrelated feature PRs (#1313 targets-frontmatter, #1321 code-intelligence) each landed a new module
  **inside this plan's Expected-surface glob** that does **not** follow the norm this plan established:
  `test_analyze_target_scope.py` (680 lines, no scaffold, over budget) and `test_corpus_lsp_honesty.py`
  (a raw `argparse.Namespace(` call).

## Routing and Merge Behavior

- Review: run 02 closed the remaining 27 **B6** sites and took **B7** to its floor.
- CI/merge: both runs landed.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `pr` stamped → `#1306`
- [x] row `landing` stamped → `landings/PLAN-080.md`
- [x] Open Defect opened — **new code landing in a converted slice does not conform, and nothing checks**
- [x] Epic scoping brief corrected — its "coverage measured in neither run" claim is **false**

## Follow-Ups

- ⛔ **The conformance-drift class is new, and it is the sharpest finding in this ingestion.** This plan's
  three strongest claims — scaffold adoption is the norm, zero hand-built namespaces, preambles at their
  floor — are **timing-sensitive assertions about a state the tree has already moved past**. This is
  structurally the same defect the epic names for *directory*-level drift (`test/pm-code-intelligence/`
  added mid-epic, four consecutive runs halting on it), but at the **file-content level inside an
  already-owned directory**, which **no document in the epic watches**. The remedy is not another sweep;
  it is a rule that fires on a non-conforming new module. Recorded in the epic's `## Open Defects` and
  folded into **PLAN-130**'s brief as the standing-enforcement question.

- ⛔ **The epic's scoping brief states "Coverage was measured in neither run" for this plan. That is
  false.** Run 01 § D5 carries an explicit before/after coverage measurement — **85% both sides**,
  17,219 → 17,340 statements, condition 2 verdict *Holds*. Only run 02 left coverage unmeasured, and it
  said so with its reasoning. `archive/README.md` is not edited (it is the frozen audit record); the
  correction is recorded here and in the epic's `## Open Defects`, and this landing record governs.

- **The 6 unconverted `test_analyze_*.py` modules are left by design, not residue** — each is
  characterised in run 01 (2-arg analyzer, subset-not-multiset assertion, results-not-findings return, no
  analyzer call, verifier-echo test). Correctly closed.

- **Stale-path residue routed to PLAN-090 landed and is confirmed fixed** (`rule-catalog.md`,
  `rule-provenance.md`, `manage-execution-manifest.py`). The stale `_fixtures.py` paths in the epic's own
  documents were routed to PLAN-120 and are now moot — those documents are this epic's read-only archive.

- **Run 6 of the module-budget campaign takes this slice and is now unblocked** — but its sizing is
  **stale**: the campaign measured 42 before this plan landed; the current figure is **49**. Corrected in
  **PLAN-140**.
