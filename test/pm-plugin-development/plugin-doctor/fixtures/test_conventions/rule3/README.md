# Rule 3 fixtures — identifier-validator-corpus

The Rule 3 tests in `test_test_conventions_rule3.py` build their fixture
trees dynamically via pytest's `tmp_path`. Each scenario writes a
synthetic validator script (with an `ID_REGEX` constant) and a stub list
command (a Python script that prints TOON `- id:` lines) so the analyzer
exercises the full `validator → regex → corpus → check` path under
hermetic isolation.

Scenarios covered (see `test_test_conventions_rule3.py`):

- `test_empty_registry_is_noop` — empty registry produces zero findings.
- `test_regex_matches_all_ids_passes` — corpus matched by regex passes.
- `test_regex_rejects_one_id_emits_finding` — a single rejected ID
  emits exactly one finding.
- `test_missing_validator_emits_error_finding` — missing validator
  surfaces a config error.
- `test_missing_constant_emits_error_finding` — missing constant
  surfaces a config error.
- `test_no_ids_in_corpus_emits_error_finding` — empty corpus surfaces a
  config error rather than silently passing.
- `test_list_command_failure_emits_error_finding` — non-zero exit from
  the list command surfaces a config error.
- `test_re_compile_pattern_extracted` — `re.compile(r"...")` extraction
  via AST.
