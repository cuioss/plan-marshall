# WS-01: Standards and Harness Foundation

epic: test-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-standards-and-harness-foundation.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Write the epic's house style (**B1**–**B10**) into the skills that own test-authoring guidance, make
the mechanical half of it enforceable by `plugin-doctor`'s `test-conventions` scope, and build the
shared harness (`parse_ns`, `load_script_module`, one `create_marshal_json` builder) that makes the
style cheap to adopt. This workstream is **blocking for every other one**: a reduction run started
before it lands invents its own harness, which is the duplication the epic exists to remove. It closes
when the style is stated, the rules fire, and the harness is importable with proof of use.

## Scope

- In scope: `marketplace/bundles/pm-dev-python/skills/pytest-testing/**`,
  `marketplace/bundles/plan-marshall/skills/persona-module-tester/**`,
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` (the `test-conventions`
  analyzers and their catalog/provenance rows), `test/conftest.py`, `test/_shared/**`,
  `test/README.md`, `test/test_shared_harness.py`, and the `test_test_conventions_rule*.py` modules
  that ship the tests for the rules added here.
- Out of scope: reducing any reduction slice (WS-02's), amending an analyzer for a defect a reduction
  run found (WS-03's), splitting a module for the line budget (WS-04's).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-010-test-authoring-standards-and-enforcement | landed | Retired the unenforced ~200-line figure for the 400-line budget; shipped four `test-conventions` rules at `severity: warning`; recorded the Hypothesis proposal without adding the dependency |
| PLAN-020-shared-test-harness | landed | `parse_ns` built from the real parser; one `create_marshal_json` builder superseding three; `test_helpers.py` retired to `_manage_config_fixtures.py`; `test/README.md` and `test/test_shared_harness.py` created |
| PLAN-180-test-fidelity-rules | staged | Fidelity rules the suite can mean: CLI-validated argv, scoped pruning, seam-pinned mirrors, behavior-cluster splits (transferred from quality-aspect 2026-09-19) |

## Sequencing and Surface Notes

- `010` and `020` may run concurrently with **each other** and with nothing else — their surfaces are
  disjoint (`010` is `marketplace/bundles/**` plus its own rule tests; `020` is `test/conftest.py`,
  `test/_shared/`, `test/README.md`).
- Both are blocking prerequisites for every plan in WS-02, WS-04, WS-05 and WS-06.
- **`010`'s own rule tests are permanently carved out of every reduction slice.** The glob
  `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` belongs to this workstream;
  `080`'s Expected surface excludes it explicitly. The one member of that set which is over the
  400-line budget is WS-04's campaign row 7, not a reduction slice's.
- **Retained defect:** `test_test_conventions_rule6.py` — the module `010` split off specifically to
  stay under the budget it was introducing — has grown back over budget. See the epic's
  `## Open Defects`.
