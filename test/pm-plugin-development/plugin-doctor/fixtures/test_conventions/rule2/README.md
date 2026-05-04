# Rule 2 fixtures — subprocess-pythonpath

The Rule 2 tests in `test_test_conventions_rule2.py` build their fixture
trees dynamically via pytest's `tmp_path`. Hermetic per-scenario test
files keep the AST shapes legible alongside the assertions and avoid
shipping syntactically broken example files in the source tree.

Scenarios covered (see `test_test_conventions_rule2.py`):

- `test_bare_subprocess_run_flagged` — `subprocess.run([sys.executable, ...])`
  without `env=` is flagged.
- `test_run_script_helper_call_passes` — calls routed through
  `conftest.run_script` are exempt.
- `test_explicit_env_pythonpath_dict_passes` — `env=` dict with a
  `PYTHONPATH` key is exempt.
- `test_env_var_named_env_treated_as_pythonpath` — `env=env` heuristic.
- `test_subprocess_run_without_sys_executable_ignored` — non-Python
  invocations ignored.
- `test_bare_run_import_form_flagged` — `from subprocess import run`
  resolves to the same rule.
- `test_dict_merge_form_with_pythonpath_passes` — Python 3.9+
  `dict | dict` merge form recognised.
- `test_env_dict_without_pythonpath_flagged` — env dict missing the
  PYTHONPATH key is still a violation.
- `test_lineno_reported_per_violation` — each finding carries source
  line numbers.
- `test_missing_test_root_returns_empty` — missing root yields zero
  findings.
