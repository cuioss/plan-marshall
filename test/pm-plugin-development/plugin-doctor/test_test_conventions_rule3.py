#!/usr/bin/env python3
"""Tests for Rule 3 (identifier-validator regex vs corpus) of doctor-test-conventions.

The rule extracts a regex literal from a registered validator file via
AST, runs the registered ``list_command``, parses IDs out of the TOON
output, and asserts the regex fullmatches every ID. Empty registry =
no-op. Lesson ``2026-04-29-10-001`` documents the original incident.
"""

import importlib.util
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_analyze_test_conventions = _load_module('_analyze_test_conventions', '_analyze_test_conventions.py')
analyze_validator_regex_vs_corpus = _analyze_test_conventions.analyze_validator_regex_vs_corpus


def _write_validator(tmp_path: Path, pattern: str) -> Path:
    """Write a synthetic validator script that defines ID_REGEX with the given pattern."""
    validator_path = tmp_path / 'validator.py'
    validator_path.write_text(
        textwrap.dedent(
            f"""
            import re

            ID_REGEX = r'{pattern}'
            COMPILED = re.compile(ID_REGEX)
            """
        ),
        encoding='utf-8',
    )
    return validator_path


def _write_list_stub(tmp_path: Path, ids: list[str]) -> str:
    """Write a stub Python script that emits TOON-shaped id: lines and return the invocation command."""
    stub_path = tmp_path / 'list_stub.py'
    body_lines = ['print("status: success")', f'print("total: {len(ids)}")']
    for identifier in ids:
        body_lines.append(f'print("- id: {identifier}")')
    stub_path.write_text('\n'.join(body_lines) + '\n', encoding='utf-8')
    return f'{sys.executable} {stub_path}'


def test_empty_registry_is_noop(tmp_path):
    """An empty registry produces zero findings."""
    findings = analyze_validator_regex_vs_corpus([], project_root=tmp_path)
    assert findings == []


def test_regex_matches_all_ids_passes(tmp_path):
    """When every corpus ID matches the regex, no findings are emitted."""
    pattern = r'\d{4}-\d{2}-\d{2}-\d{2}-\d{3}'
    validator = _write_validator(tmp_path, pattern)
    list_command = _write_list_stub(tmp_path, ['2026-04-29-22-001', '2026-05-02-01-001'])

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(validator),
                'regex_constant': 'ID_REGEX',
                'list_command': list_command,
            }
        ],
        project_root=tmp_path,
    )

    assert findings == []


def test_regex_rejects_one_id_emits_finding(tmp_path):
    """A regex that rejects a real ID produces one finding per rejection."""
    pattern = r'\d{4}-\d{2}-\d{2}-\d{2}-\d{3}'
    validator = _write_validator(tmp_path, pattern)
    list_command = _write_list_stub(
        tmp_path,
        ['2026-04-29-22-001', '2026-05-02-XX-001'],  # second ID is malformed
    )

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(validator),
                'regex_constant': 'ID_REGEX',
                'list_command': list_command,
            }
        ],
        project_root=tmp_path,
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == 'identifier-validator-corpus'
    assert finding['details']['rejected_id'] == '2026-05-02-XX-001'
    assert finding['details']['pattern'] == pattern


def test_missing_validator_emits_error_finding(tmp_path):
    """Validator path not found surfaces a config error finding (not a match)."""
    list_command = _write_list_stub(tmp_path, ['2026-04-29-22-001'])

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(tmp_path / 'missing.py'),
                'regex_constant': 'ID_REGEX',
                'list_command': list_command,
            }
        ],
        project_root=tmp_path,
    )

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'validator_not_found'


def test_missing_constant_emits_error_finding(tmp_path):
    """Validator file present but constant missing surfaces a config error finding."""
    validator = _write_validator(tmp_path, r'\d+')
    list_command = _write_list_stub(tmp_path, ['1'])

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(validator),
                'regex_constant': 'NOT_DEFINED_REGEX',
                'list_command': list_command,
            }
        ],
        project_root=tmp_path,
    )

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'regex_constant_not_found'


def test_no_ids_in_corpus_emits_error_finding(tmp_path):
    """When the list command yields no id: lines, surface a config error rather than passing silently."""
    validator = _write_validator(tmp_path, r'\d+')
    list_command = _write_list_stub(tmp_path, [])

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(validator),
                'regex_constant': 'ID_REGEX',
                'list_command': list_command,
            }
        ],
        project_root=tmp_path,
    )

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'no_ids_in_corpus'


def test_list_command_failure_emits_error_finding(tmp_path):
    """A list command that exits non-zero surfaces a config error finding."""
    validator = _write_validator(tmp_path, r'\d+')
    failing_command = f'{sys.executable} -c "import sys; sys.exit(2)"'

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(validator),
                'regex_constant': 'ID_REGEX',
                'list_command': failing_command,
            }
        ],
        project_root=tmp_path,
    )

    assert len(findings) == 1
    assert findings[0]['details']['reason'].startswith('list_command_failed')


def test_re_compile_pattern_extracted(tmp_path):
    """Regex literal embedded inside ``re.compile(r"...")`` is extracted correctly."""
    validator = tmp_path / 'compiled_validator.py'
    validator.write_text(
        textwrap.dedent(
            """
            import re

            ID_REGEX = re.compile(r'\\d{2}')
            """
        ),
        encoding='utf-8',
    )
    list_command = _write_list_stub(tmp_path, ['12', '34'])

    findings = analyze_validator_regex_vs_corpus(
        [
            {
                'validator_path': str(validator),
                'regex_constant': 'ID_REGEX',
                'list_command': list_command,
            }
        ],
        project_root=tmp_path,
    )

    assert findings == []
