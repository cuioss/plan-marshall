# Landing Analysis: PLAN-020 — The Shared Test Harness

epic: test-quality
workstream: WS-01
pr: not recorded in the archived report (cloud-lane run, pre-ingestion)

> Landing record for one shipped plan. Lives at `landings/PLAN-020.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Ground-truth check run at HEAD `2cd1a19c`** by a dispatched read-only `execution-context-level-3`
leaf, against the archived `plan.md` + `report-01.md`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `parse_ns(bundle, skill, script, *argv)` built from the real parser, with a named error when no seam exists | **shipped-modified** | `test/conftest.py:710` `def parse_ns(`. The shipped design intercepts `main()` rather than reaching a parser seam — the run **refuted its own parser-seam hypothesis** and recorded the change. The contract D1 stated is met; the mechanism is not the one specified |
| D2 — one `create_marshal_json` builder with named presets, superseding three definitions | **shipped-as-specified** | `grep -rn 'def create_marshal_json' test --include=*.py` returns exactly **one** hit (`test/conftest.py:1916`); `test_triage_extension.py` now imports it rather than defining its own |
| D3 — retire `test_helpers.py` to `_manage_config_fixtures.py`, repointing ~23 importers | **shipped-as-specified** | `test/plan-marshall/manage-config/_manage_config_fixtures.py` exists; `test_helpers.py` is absent; **0** modules import `test_helpers`; **24** import `_manage_config_fixtures` (report said 23 — one added since, drift not defect) |
| D4 — `test/README.md`, the navigation and ownership document | **shipped-as-specified** | `test/README.md` exists and cross-references the standards |
| D5 — `test/test_shared_harness.py`, meta-tests for `parse_ns`, the presets, and a whole-tree D3 guard | **shipped-as-specified** | `test/test_shared_harness.py` exists |
| D6 — convert up to 10 modules across ≥4 subtrees as proof of use, reporting the line delta | **shipped-as-specified** | All **7** named modules exist at their claimed paths across **5** distinct subtrees, satisfying the ≥4 floor. The 10 was a ceiling, not a target |

**Five of six shipped as specified; one shipped-modified with the modification recorded.** D1's
deviation is the good kind: the run tested its own hypothesis against the implementing source, found it
false, and changed the mechanism rather than the contract.

## Metrics and Anomalies

- Collected-item count: the report claims 20,059 before and after (excluding D5's own 21 new tests) —
  the load-bearing no-tests-lost check. **Not re-verified here**: re-running collection is a build, which
  is outside the orchestrator's small-ops boundary. Recorded as *claimed, unverified*.
- Anomalies: none in the run itself.

## Routing and Merge Behavior

- Review: not recoverable from the archived artifacts.
- CI/merge: landed on `main`; the shipped helpers are importable at HEAD, which is the stronger evidence.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `landing` stamped → `landings/PLAN-020.md`
- [x] Open Defect opened — `create_nested_marshal_json` is a third marshal builder by behaviour

## Follow-Ups

- **Open Defect — D2 collapsed three builders into one and left a fourth.**
  `create_nested_marshal_json` in `_manage_config_fixtures.py` remains a distinct marshal builder by
  behaviour. The archived report records it; **no plan owns it.** Recorded in the epic's
  `## Open Defects`.

- **Closed since landing, correctly:** `load_script_module` could not reach a skill-root `extension.py`
  — assigned to `090` § D2 and discharged there. The `testing-standards.md` shape that D5's guard
  fails the build on was corrected by a separate PR outside this epic.

- **Still open and unowned:** `uv.lock` out of sync with `pyproject.toml` on `main` (shared with
  PLAN-010's residue; recorded once in the epic's `## Open Defects`).

- **Not a defect in this plan, recorded so it is not mis-read:** `020`'s scope was explicitly capped at
  ≤10 proof-of-use conversions and it met that. Corpus-wide `parse_ns` adoption standing at 36 modules
  is the reduction slices' work, not this plan's shortfall.

## Note on Drift

`spec_from_file_location` preambles stood at 204 whole-tree when this plan landed and at **63** at HEAD —
a large reduction driven by the reduction plans that ran afterwards. Expected drift, not a report defect.
