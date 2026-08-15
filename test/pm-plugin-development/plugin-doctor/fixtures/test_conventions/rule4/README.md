# Rule 4-7 fixtures — the warning-severity house-style rules

The tests in `test_test_conventions_rule4.py` build their fixture trees
dynamically via pytest's `tmp_path` rather than checking in static fixture
files, matching the convention of the three sibling rule directories. Dynamic
construction keeps each scenario hermetic (no cross-test contamination) and
reads more clearly — the fixture shape lives next to the assertion that
depends on it.

Static fixtures would additionally be self-defeating here: three of these four
rules fire on properties of a checked-in file (its line count, its name, its
import preamble), so a static fixture tree would trip the rules against the
real `test/` tree during a whole-tree sweep and inflate every count the plan
measures.

Scenarios covered (see `test_test_conventions_rule4.py`):

**`test-module-line-budget`**

- `test_module_over_budget_is_flagged` — a collected module over 400 lines.
- `test_module_within_budget_is_not_flagged` — negative control.
- `test_line_budget_finding_carries_count_and_budget` — the finding reports
  line count, budget, and overage.
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

**`test-module-preamble-boilerplate`**

- `test_spec_from_file_location_is_flagged` — hand-rolled loader preamble.
- `test_deep_parent_chain_is_flagged` — a depth-3 `.parent` chain, with its
  depth in the finding details.
- `test_shallow_parent_chain_is_not_flagged` — a depth-2 hop is ordinary path
  work.
- `test_conftest_helpers_are_not_flagged` — the sanctioned helpers.
- `test_one_chain_yields_one_finding` — a depth-4 chain reports once, not once
  per suffix.

**`test-docstring-historical-prose`**

- `test_lesson_id_in_docstring_is_flagged` — lesson-id citation.
- `test_pr_reference_in_docstring_is_flagged` — PR citation.
- `test_plan_deliverable_id_in_comment_is_flagged` — comments are prose too.
- `test_present_tense_docstring_is_not_flagged` — negative control.
- `test_citation_shape_as_string_data_is_not_flagged` — the rule's structural
  discriminator: the same shape as string-literal test data is not a citation.
- `test_one_finding_per_prose_segment` — one finding per segment, not per
  matching pattern.

**Shared**

- `test_missing_test_root_is_a_noop` — every rule returns no findings when the
  test root does not exist.
