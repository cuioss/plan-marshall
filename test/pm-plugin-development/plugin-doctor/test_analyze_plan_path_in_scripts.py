# ruff: noqa: I001, E402
"""Tests for the ``plan-path-in-scripts`` rule analyzer.

The analyzer detects occurrences of the literal string ``.plan/plans/`` inside
Python files in the marketplace bundle scripts tree.  Code-literal occurrences
in production scripts are flagged (the canonical helper is
``tools-file-ops:file_ops.get_plan_dir``); docstring-only occurrences and
self-referential occurrences in the analyzer itself are skipped.

Test layers:
  * End-to-end scan distinguishing a production hit from a whitelisted hit.
  * ``_classify`` returns ``production_script`` for code-literal hits and
    ``test_assertion`` for hits in test directories.
  * Whitelist excludes the analyzer's self-referential occurrence.
  * Empty marketplace tree returns ``[]``.
  * ``_scan_file`` emits one finding per code-literal occurrence (multi-hit).
  * ``.plan/plans/`` inside a triple-quoted docstring produces zero findings.
"""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_appis = _load_module(
    '_analyze_plan_path_in_scripts', '_analyze_plan_path_in_scripts.py'
)

analyze_plan_path_in_scripts = _appis.analyze_plan_path_in_scripts
is_whitelisted = _appis.is_whitelisted
_classify = _appis._classify
_scan_file = _appis._scan_file
RULE_ID = _appis.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_marketplace(tmp_path: Path) -> Path:
    """Create ``marketplace/bundles/`` skeleton. Returns marketplace root."""
    mp = tmp_path / 'marketplace'
    (mp / 'bundles').mkdir(parents=True)
    return mp


def _write_py(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


# ===========================================================================
# Fixture a: end-to-end — one production hit + one whitelisted hit
# ===========================================================================


class TestEndToEndScan:
    """End-to-end scan distinguishes a production hit from a whitelisted hit."""

    def test_production_hit_emitted_whitelisted_skipped(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)

        # Production hit: a real .plan/plans/ literal in a production script.
        prod_py = (
            mp
            / 'bundles'
            / 'my-bundle'
            / 'skills'
            / 'my-skill'
            / 'scripts'
            / 'do_work.py'
        )
        _write_py(
            prod_py,
            '# Production script\nplan_dir = ".plan/plans/" + plan_id\n',
        )

        # Whitelisted: the analyzer's own self-referential occurrence.
        whitelisted_py = (
            mp
            / 'bundles'
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'scripts'
            / '_analyze_plan_path_in_scripts.py'
        )
        _write_py(
            whitelisted_py,
            '# Self-referential analyzer\n_MARKER = ".plan/plans/"\n',
        )

        findings = analyze_plan_path_in_scripts(mp)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['category'] == 'production_script'
        assert str(prod_py) == f['file']
        assert '.plan/plans/' in f['snippet']


# ===========================================================================
# Fixture b: _classify behaviour — production_script vs test_assertion
# ===========================================================================


class TestClassify:
    """``_classify`` distinguishes production scripts from test files."""

    def test_production_script_classification(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'do_work.py'
        )
        assert _classify(path) == 'production_script'

    def test_test_directory_classified_as_test(self, tmp_path: Path) -> None:
        path = tmp_path / 'test' / 'plan-marshall' / 'foo' / 'test_bar.py'
        assert _classify(path) == 'test_assertion'

    def test_tests_directory_classified_as_test(self, tmp_path: Path) -> None:
        path = tmp_path / 'tests' / 'foo' / 'test_bar.py'
        assert _classify(path) == 'test_assertion'

    def test_test_prefix_filename_classified_as_test(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'test_runner.py'
        )
        assert _classify(path) == 'test_assertion'

    def test_test_suffix_filename_classified_as_test(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'runner_test.py'
        )
        assert _classify(path) == 'test_assertion'


# ===========================================================================
# Fixture c: whitelist correctness — self-referential file excluded
# ===========================================================================


class TestWhitelist:
    """The whitelist excludes the analyzer's own self-referential occurrence."""

    def test_self_file_whitelisted(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'scripts'
            / '_analyze_plan_path_in_scripts.py'
        )
        assert is_whitelisted(path)

    def test_arbitrary_other_path_not_whitelisted(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'do_work.py'
        )
        assert not is_whitelisted(path)

    def test_similar_name_but_different_filename_not_whitelisted(
        self, tmp_path: Path
    ) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / '_analyze_plan_path_in_scripts_helper.py'
        )
        assert not is_whitelisted(path)


# ===========================================================================
# Fixture d: empty marketplace tree returns []
# ===========================================================================


class TestEmptyMarketplace:
    """Empty marketplace tree returns no findings."""

    def test_empty_bundles_directory(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_nonexistent_marketplace_root(self, tmp_path: Path) -> None:
        mp = tmp_path / 'does-not-exist'
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_bundles_without_marker(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / 'clean.py'
        _write_py(py, '# Nothing of interest\ndef do_work():\n    return 42\n')
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []


# ===========================================================================
# Fixture e: _scan_file emits one finding per code-literal occurrence
# ===========================================================================


class TestMultiHitInSingleFile:
    """``_scan_file`` emits a separate finding per code-literal occurrence."""

    def test_multiple_code_literal_occurrences(self, tmp_path: Path) -> None:
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'multi.py'
        )
        _write_py(
            py,
            '# Two code-literal hits\n'
            'a = ".plan/plans/" + plan_id\n'
            'b = ".plan/plans/" + other_id\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 2
        # Hits land on the two distinct lines (lines 2 and 3 of the file).
        line_numbers = sorted(f['line'] for f in findings)
        assert line_numbers == [2, 3]
        for f in findings:
            assert f['rule_id'] == RULE_ID
            assert f['category'] == 'production_script'
            assert '.plan/plans/' in f['snippet']


# ===========================================================================
# Fixture f: docstring-only occurrence produces zero findings
# ===========================================================================


class TestDocstringSkip:
    """``.plan/plans/`` inside a triple-quoted docstring produces zero findings."""

    def test_docstring_only_occurrence_skipped(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'docstring_only.py'
        )
        # Triple-quoted docstring contains the marker; no code-literal hit.
        _write_py(
            py,
            '"""Module docstring.\n\nExample: .plan/plans/{plan_id} is the legacy form.\n"""\n\n'
            'def do_work():\n    return 42\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_single_quote_triple_docstring_skipped(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'single_quote_docstring.py'
        )
        _write_py(
            py,
            "'''Module docstring.\n\n.plan/plans/ inside single-quote triple block.\n'''\n\n"
            'def do_work():\n    return 42\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == []

    def test_mixed_docstring_and_code_literal(self, tmp_path: Path) -> None:
        """Docstring hit is skipped but the code-literal hit is reported."""
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'mixed.py'
        )
        _write_py(
            py,
            '"""Doc: .plan/plans/{id} legacy form."""\n\n'
            'plan_dir = ".plan/plans/" + plan_id\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert len(findings) == 1
        assert findings[0]['category'] == 'production_script'
        # Line 3 holds the code-literal hit (line 1 is the docstring).
        assert findings[0]['line'] == 3
