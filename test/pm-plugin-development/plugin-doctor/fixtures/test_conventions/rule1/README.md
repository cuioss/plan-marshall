# Rule 1 fixtures — unique-fixture-basenames

The Rule 1 tests in `test_test_conventions_rule1.py` build their fixture trees
dynamically via pytest's `tmp_path` rather than checking in static fixture
files. Dynamic construction keeps each test scenario hermetic (no cross-test
contamination), reads more clearly (the fixture shape lives next to the
assertion that depends on it), and avoids the `_fixtures.py` collision the
rule itself enforces.

Scenarios covered (see `test_test_conventions_rule1.py`):

- `test_clean_tree_emits_no_findings` — domain-prefixed helpers in different
  directories, no findings.
- `test_generic_basename_fixtures_flagged` — bare `_fixtures.py` flagged.
- `test_generic_basename_helpers_and_common_flagged` — bare `_helpers.py` and
  `_common.py` flagged.
- `test_cross_directory_collision_reports_both` — sibling dirs with the same
  domain-prefixed basename, both flagged.
- `test_generic_name_in_two_dirs_only_emits_generic_findings` — generic
  takes precedence over the collision branch.
- `test_init_files_are_ignored` — dunder files excluded.
- `test_missing_test_root_returns_empty` — missing root yields zero findings.
- `test_finding_carries_standard_anchor` — finding details include the doc
  anchor for cross-reference resolution.
