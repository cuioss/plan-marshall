# ruff: noqa: I001, E402
"""Tests for the ``plan-path-in-scripts`` rule analyzer.

The analyzer detects drift from the canonical ``tools-file-ops:file_ops``
path helpers via AST analysis.  Two forms are detected:

- **Form A** (literal bypass): an ``ast.Constant`` string node whose value
  contains ``.plan/plans/`` (without ``/local/``).
- **Form B** (parent-walking re-derivation): a ``Path(__file__).parent…``
  or ``os.path.dirname(__file__)`` chain joined against a ``.plan``-domain
  subdirectory name (``plans``, ``lessons-learned``, ``logs``,
  ``archived-plans``, ``workspace``).

Exemptions asserted not-flagged:
  * ``sys.path.insert`` / ``sys.path.append`` bootstrap chains (form B).
  * ``file_ops.py`` (the canonical source — whitelist entry).

Test layers:
  * End-to-end scan distinguishing a production hit from a whitelisted hit.
  * ``_classify`` returns ``production_script`` for code-literal hits and
    ``test_assertion`` for hits in test directories.
  * Whitelist excludes the analyzer's self-referential occurrence AND
    ``file_ops.py``.
  * Empty marketplace tree returns ``[]``.
  * ``_scan_file`` emits one finding per code-literal occurrence (multi-hit).
  * ``.plan/plans/`` inside a triple-quoted docstring produces zero findings.
  * Form A no-regression: ``.plan/plans/`` (without ``/local/``) still flagged;
    ``.plan/local/plans/`` is NOT flagged.
  * Form B literal bypass detected.
  * Form B parent-walking re-derivation detected.
  * ``sys.path.insert`` bootstrap exemption NOT flagged.
  * ``file_ops.py`` canonical-source exemption NOT flagged.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_appis = _load_module(
    '_analyze_plan_path_in_scripts', '_analyze_plan_path_in_scripts.py'
)

analyze_plan_path_in_scripts = _appis.analyze_plan_path_in_scripts
is_whitelisted = _appis.is_whitelisted
_classify = _appis._classify
_scan_file = _appis._scan_file
RULE_ID = _appis.RULE_ID
_PLAN_DOMAIN_DIRS = _appis._PLAN_DOMAIN_DIRS


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


# ===========================================================================
# Fixture g: Form A no-regression — .plan/plans/ (without /local/) still
# flagged; .plan/local/plans/ (canonical form) is NOT flagged.
# ===========================================================================


class TestFormANoRegression:
    """No-regression: original .plan/plans/ literal detection still fires."""

    def test_plan_plans_without_local_flagged(self, tmp_path: Path) -> None:
        """The drifted .plan/plans/ form is still flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(py, 'plan_dir = ".plan/plans/" + plan_id\n')
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert '.plan/plans/' in findings[0]['snippet']

    def test_plan_local_plans_not_flagged(self, tmp_path: Path) -> None:
        """The canonical .plan/local/plans/ form is NOT flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(py, 'plan_dir = ".plan/local/plans/" + plan_id\n')
        findings = _scan_file(py)
        assert findings == []


# ===========================================================================
# Fixture h: Form B — parent-walking re-derivation detected
# ===========================================================================


class TestFormBParentWalking:
    """Form B: Path(__file__).parent chain joined to a .plan-domain dir."""

    def test_path_file_parent_plans_flagged(self, tmp_path: Path) -> None:
        """Path(__file__).parent / "plans" is form-B drift and must be flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'PLAN_DIR = Path(__file__).parent / "plans"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['line'] == 2

    def test_os_path_dirname_plans_flagged(self, tmp_path: Path) -> None:
        """os.path.dirname(__file__) joined to a .plan-domain dir is form-B drift."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'import os\n'
            'import os.path\n'
            'PLAN_DIR = os.path.join(os.path.dirname(__file__), "plans")\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['line'] == 3

    def test_nested_parent_lessons_flagged(self, tmp_path: Path) -> None:
        """Multi-level parent chain joined to lessons-learned is flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'LESSONS = Path(__file__).parent.parent / "lessons-learned"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1
        assert findings[0]['line'] == 2

    def test_parent_chain_logs_domain_flagged(self, tmp_path: Path) -> None:
        """Parent chain joined to 'logs' (a .plan-domain dir) is flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'LOG_DIR = Path(__file__).parent / "logs"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1

    def test_parent_chain_non_plan_domain_not_flagged(self, tmp_path: Path) -> None:
        """Parent chain joined to a non-.plan-domain dir is NOT flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'DATA_DIR = Path(__file__).parent / "data"\n',
        )
        findings = _scan_file(py)
        assert findings == []

    def test_plan_domain_dirs_constant_imported(self) -> None:
        """Verify the expected .plan-domain dirs are present in the constant."""
        assert 'plans' in _PLAN_DOMAIN_DIRS
        assert 'lessons-learned' in _PLAN_DOMAIN_DIRS
        assert 'logs' in _PLAN_DOMAIN_DIRS
        assert 'archived-plans' in _PLAN_DOMAIN_DIRS
        assert 'workspace' in _PLAN_DOMAIN_DIRS


# ===========================================================================
# Fixture i: sys.path.insert exemption — bootstrap chains NOT flagged
# ===========================================================================


class TestSysPathInsertExemption:
    """sys.path.insert / sys.path.append bootstrap chains are NOT flagged."""

    def test_sys_path_insert_with_plans_domain_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """sys.path.insert(0, Path(__file__).parent / "plans") is a bootstrap
        idiom and must NOT produce a form-B finding.
        """
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'import sys\n'
            'from pathlib import Path\n'
            'sys.path.insert(0, str(Path(__file__).parent / "plans"))\n',
        )
        findings = _scan_file(py)
        assert findings == [], (
            'sys.path.insert bootstrap must not be flagged as form-B drift'
        )

    def test_sys_path_append_exemption(self, tmp_path: Path) -> None:
        """sys.path.append(Path(__file__).parent / "logs") is also exempt."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'import sys\n'
            'from pathlib import Path\n'
            'sys.path.append(str(Path(__file__).parent / "logs"))\n',
        )
        findings = _scan_file(py)
        assert findings == [], (
            'sys.path.append bootstrap must not be flagged as form-B drift'
        )

    def test_non_sys_path_same_pattern_flagged(self, tmp_path: Path) -> None:
        """The same parent-chain pattern outside a sys.path call IS flagged."""
        py = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'work.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            'MY_DIR = Path(__file__).parent / "plans"\n',
        )
        findings = _scan_file(py)
        assert len(findings) == 1, (
            'parent chain outside sys.path call must be flagged as form-B drift'
        )


# ===========================================================================
# Fixture j: file_ops.py canonical-source exemption
# ===========================================================================


class TestFileOpsExemption:
    """file_ops.py (tools-file-ops bundle) is whitelisted — never flagged."""

    def test_file_ops_path_whitelisted(self, tmp_path: Path) -> None:
        """The path tools-file-ops/.../file_ops.py is whitelisted."""
        path = (
            tmp_path
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py'
        )
        assert is_whitelisted(path)

    def test_file_ops_with_plan_plans_literal_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """A file_ops.py containing .plan/plans/ is silently skipped."""
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py'
        )
        _write_py(py, 'canonical = ".plan/plans/" + plan_id\n')
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == [], (
            'file_ops.py must be whitelisted and produce no findings'
        )

    def test_file_ops_with_parent_chain_not_flagged(self, tmp_path: Path) -> None:
        """file_ops.py containing a parent-walking chain is silently skipped."""
        mp = _make_marketplace(tmp_path)
        py = (
            mp
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'tools-file-ops'
            / 'scripts'
            / 'file_ops.py'
        )
        _write_py(
            py,
            'from pathlib import Path\n'
            '_BASE = Path(__file__).parent / "plans"\n',
        )
        findings = analyze_plan_path_in_scripts(mp)
        assert findings == [], (
            'file_ops.py parent-chain must be whitelisted and produce no findings'
        )
