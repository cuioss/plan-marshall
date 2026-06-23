#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the argparse_safety rule in plugin-doctor.

The rule statically scans Python scripts under
``marketplace/bundles/*/skills/*/scripts/`` and ``marketplace/targets/``
for ``ArgumentParser(...)`` and ``subparsers.add_parser(...)`` calls that
are missing ``allow_abbrev=False``. Missing the flag silently enables
argparse's prefix-matching behavior, which lets retired or renamed flags
keep matching by accident — see lesson 2026-04-17-012.

Tests here exercise the scanner via direct import (Tier 2) against
synthetic fixture trees.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_doctor_analysis = _load_module('_doctor_analysis', '_doctor_analysis.py')
scan_argparse_safety = _doctor_analysis.scan_argparse_safety
_scan_file_for_argparse_safety = _doctor_analysis._scan_file_for_argparse_safety
_is_test_path = _doctor_analysis._is_test_path


# =============================================================================
# Single-file scanner
# =============================================================================


def _write_script(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding='utf-8')
    return path


def test_argumentparser_missing_flag_flagged(tmp_path):
    """ArgumentParser() without allow_abbrev=False emits one finding."""
    script = _write_script(
        tmp_path,
        'my_script.py',
        "import argparse\nparser = argparse.ArgumentParser(description='x')\n",
    )
    findings = _scan_file_for_argparse_safety(script)
    assert len(findings) == 1
    assert findings[0]['type'] == 'argparse_safety'
    assert findings[0]['severity'] == 'error'
    assert findings[0]['fixable'] is False
    assert findings[0]['call'] == 'ArgumentParser'
    assert 'allow_abbrev=False' in findings[0]['description']
    assert findings[0]['file'] == str(script)
    assert findings[0]['line'] == 2


def test_argumentparser_with_flag_not_flagged(tmp_path):
    """ArgumentParser(allow_abbrev=False) produces no findings."""
    script = _write_script(
        tmp_path,
        'my_script.py',
        "import argparse\nparser = argparse.ArgumentParser(description='x', allow_abbrev=False)\n",
    )
    findings = _scan_file_for_argparse_safety(script)
    assert findings == []


def test_add_parser_missing_flag_flagged(tmp_path):
    """subparsers.add_parser() without allow_abbrev=False is flagged."""
    script = _write_script(
        tmp_path,
        'my_script.py',
        'import argparse\n'
        'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        'subparsers = parser.add_subparsers()\n'
        "p_a = subparsers.add_parser('a', help='A')\n",
    )
    findings = _scan_file_for_argparse_safety(script)
    assert len(findings) == 1
    assert findings[0]['call'] == 'add_parser'
    assert findings[0]['line'] == 4


def test_add_parser_with_flag_not_flagged(tmp_path):
    """subparsers.add_parser(..., allow_abbrev=False) produces no findings."""
    script = _write_script(
        tmp_path,
        'my_script.py',
        'import argparse\n'
        'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        'subparsers = parser.add_subparsers()\n'
        "p_a = subparsers.add_parser('a', help='A', allow_abbrev=False)\n",
    )
    findings = _scan_file_for_argparse_safety(script)
    assert findings == []


def test_allow_abbrev_true_is_flagged(tmp_path):
    """allow_abbrev=True is still a violation — only the literal False value passes."""
    script = _write_script(
        tmp_path,
        'my_script.py',
        'import argparse\nparser = argparse.ArgumentParser(allow_abbrev=True)\n',
    )
    findings = _scan_file_for_argparse_safety(script)
    assert len(findings) == 1


def test_multiple_violations_in_one_file(tmp_path):
    """All missing-flag calls in a single file are reported."""
    script = _write_script(
        tmp_path,
        'multi.py',
        'import argparse\n'
        'a = argparse.ArgumentParser()\n'
        'b = argparse.ArgumentParser(allow_abbrev=False)\n'
        'subs = b.add_subparsers()\n'
        "c = subs.add_parser('c')\n"
        "d = subs.add_parser('d', allow_abbrev=False)\n",
    )
    findings = _scan_file_for_argparse_safety(script)
    lines = sorted(f['line'] for f in findings)
    assert lines == [2, 5]


def test_bare_constructor_call_matches(tmp_path):
    """Bare ``ArgumentParser(...)`` (from-import) call is also flagged."""
    script = _write_script(
        tmp_path,
        'bare.py',
        "from argparse import ArgumentParser\nparser = ArgumentParser(description='x')\n",
    )
    findings = _scan_file_for_argparse_safety(script)
    assert len(findings) == 1
    assert findings[0]['call'] == 'ArgumentParser'


def test_unrelated_parser_names_not_flagged(tmp_path):
    """Unrelated classes named ``ArgumentParser``/``add_parser`` are not matched?

    The rule is a static pattern match and intentionally does not resolve
    identifiers. In practice this is acceptable because the rule scope is
    ``scripts/`` and ``targets/``, where the short names are reserved for
    argparse usage. The test documents the behavior: any ``ArgumentParser``
    call gets flagged, ensuring no false negatives for the target case.
    """
    script = _write_script(
        tmp_path,
        'other.py',
        'class MyCustomThing:\n    pass\nx = MyCustomThing()\n',
    )
    findings = _scan_file_for_argparse_safety(script)
    assert findings == []


def test_syntax_error_is_tolerated(tmp_path):
    """Files that fail to parse return no findings (do not raise)."""
    script = _write_script(tmp_path, 'broken.py', 'def oops(\n')
    findings = _scan_file_for_argparse_safety(script)
    assert findings == []


# =============================================================================
# Test-path exclusion
# =============================================================================


def test_is_test_path_recognizes_test_dirs(tmp_path):
    assert _is_test_path(tmp_path / 'test' / 'something.py')
    assert _is_test_path(tmp_path / 'tests' / 'something.py')
    assert _is_test_path(tmp_path / 'pkg' / 'test' / 'foo.py')


def test_is_test_path_recognizes_test_filenames(tmp_path):
    assert _is_test_path(tmp_path / 'test_foo.py')
    assert _is_test_path(tmp_path / 'foo_test.py')


def test_is_test_path_ignores_production_files(tmp_path):
    assert not _is_test_path(tmp_path / 'foo.py')
    assert not _is_test_path(tmp_path / 'pkg' / 'foo.py')
    # 'latest' contains 'test' as a substring but is not a path component
    assert not _is_test_path(tmp_path / 'latest' / 'foo.py')


# =============================================================================
# Marketplace-wide scan — fixture + real tree
# =============================================================================


def test_scan_argparse_safety_on_fixture(tmp_path):
    """Build a fake marketplace tree and verify missing-flag calls are flagged
    while test files are excluded."""
    marketplace_root = tmp_path / 'marketplace' / 'bundles'
    scripts_dir = marketplace_root / 'fake-bundle' / 'skills' / 'fake-skill' / 'scripts'
    scripts_dir.mkdir(parents=True)

    # Bad: missing flag
    (scripts_dir / 'bad.py').write_text('import argparse\nparser = argparse.ArgumentParser()\n')
    # Good: has flag
    (scripts_dir / 'good.py').write_text('import argparse\nparser = argparse.ArgumentParser(allow_abbrev=False)\n')
    # Test file: MUST be excluded even if missing the flag
    (scripts_dir / 'test_excluded.py').write_text('import argparse\nparser = argparse.ArgumentParser()\n')
    # Test directory: MUST be excluded
    test_dir = scripts_dir / 'test'
    test_dir.mkdir()
    (test_dir / 'nested.py').write_text('import argparse\nparser = argparse.ArgumentParser()\n')

    # Targets tree alongside bundles/
    targets_dir = tmp_path / 'marketplace' / 'targets'
    targets_dir.mkdir()
    (targets_dir / 'generate.py').write_text('import argparse\nparser = argparse.ArgumentParser()\n')
    # Nested module under a per-target package
    nested = targets_dir / 'opencode'
    nested.mkdir()
    (nested / 'emitter.py').write_text('import argparse\nparser = argparse.ArgumentParser()\n')

    findings = scan_argparse_safety(marketplace_root)
    flagged_files = {Path(f['file']).name for f in findings}
    assert flagged_files == {'bad.py', 'generate.py', 'emitter.py'}, (
        f'Expected bad.py, generate.py, and emitter.py to be flagged, got {flagged_files}'
    )
    assert all(f['type'] == 'argparse_safety' for f in findings)
    assert all(f['severity'] == 'error' for f in findings)
