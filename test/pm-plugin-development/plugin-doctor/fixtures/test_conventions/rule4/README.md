# Rule 4-5 fixtures — the module-shape rules

`test_test_conventions_rule4.py` covers the two warning-severity rules that
govern whether a module is the right shape to be collected at all:
`test-module-line-budget` and `test-helper-module-misnamed`. The module-content
rules live in `test_test_conventions_rule6.py` (see `../rule6/`).

The tests build their fixture trees dynamically via pytest's `tmp_path` rather
than checking in static fixture files, matching the convention of the sibling
rule directories. Dynamic construction keeps each scenario hermetic and reads
more clearly — the fixture shape lives next to the assertion that depends on it.

Static fixtures would additionally be self-defeating here: both rules fire on
properties of a checked-in file (its line count, its name), so a static fixture
tree would trip them against the real `test/` tree during a whole-tree sweep and
inflate every count the standards measure.

Scenarios covered:

**`test-module-line-budget`**

- `test_module_over_budget_is_flagged` — a collected module over 400 lines.
- `test_module_within_budget_is_not_flagged` — negative control.
- `test_line_budget_finding_carries_count_and_budget` — the finding reports line
  count, budget, and overage.
- `test_uncollected_module_over_budget_is_not_flagged` — a helper module over
  budget is out of scope.

**`test-helper-module-misnamed`**

- `test_collected_module_without_tests_is_flagged` — `test_*.py` declaring no
  test.
- `test_collected_module_with_test_function_is_not_flagged` — negative control.
- `test_collected_module_with_test_class_is_not_flagged` — a `Test*` class
  counts as a declared test.
- `test_underscore_helper_without_tests_is_not_flagged` — a correctly-named
  helper is never collected.
- `test_trailing_suffix_collected_module_is_flagged` — the `*_test.py` pattern
  is covered, not only `test_*.py`.

**Shared**

- `test_missing_test_root_is_a_noop` — both rules return no findings when the
  test root does not exist.
