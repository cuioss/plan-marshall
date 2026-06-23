# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``executor-path-in-production`` rule analyzer.

The analyzer detects occurrences of ``.plan/execute-script.py`` inside Python
files in the marketplace bundle scripts tree.  Whitelisted categories (executor
generator, lint analyzers, permission tooling) are silently skipped.

Test layers:
  * Whitelisted generator → no finding (fixture a).
  * Whitelisted lint-analyzer reference → no finding (fixture b).
  * Non-whitelisted production script → finding with category ``production_script`` (fixture c).
  * Test-assertion occurrence → finding with category ``test_assertion`` (fixture d).
  * End-to-end: ``analyze_executor_path_in_production`` scanning a minimal marketplace tree.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_aepip = _load_module(
    '_analyze_executor_path_in_production', '_analyze_executor_path_in_production.py'
)

analyze_executor_path_in_production = _aepip.analyze_executor_path_in_production
is_whitelisted = _aepip.is_whitelisted
RULE_ID = _aepip.RULE_ID


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
# Fixture a: whitelisted generator — no finding
# ===========================================================================


class TestWhitelistedGenerator:
    """The executor generator script is whitelisted."""

    def test_generate_executor_is_whitelisted(self, tmp_path: Path) -> None:
        path = tmp_path / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
        assert is_whitelisted(path)

    def test_template_is_whitelisted(self, tmp_path: Path) -> None:
        path = tmp_path / 'tools-script-executor' / 'templates' / 'execute-script.py.template'
        assert is_whitelisted(path)

    def test_no_finding_from_generator(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
        _write_py(
            py,
            '# Generator\nEXECUTOR_PATH = ".plan/execute-script.py"\n',
        )
        findings = analyze_executor_path_in_production(mp)
        assert findings == []


# ===========================================================================
# Fixture b: whitelisted lint-analyzer reference — no finding
# ===========================================================================


class TestWhitelistedLintAnalyzer:
    """Lint analyzers that inspect markdown for executor notation are whitelisted."""

    def test_analyze_verb_chains_whitelisted(self, tmp_path: Path) -> None:
        path = tmp_path / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / '_analyze_verb_chains.py'
        assert is_whitelisted(path)

    def test_analyze_markdown_whitelisted(self, tmp_path: Path) -> None:
        path = tmp_path / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / '_analyze_markdown.py'
        assert is_whitelisted(path)

    def test_this_file_whitelisted(self, tmp_path: Path) -> None:
        path = tmp_path / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / '_analyze_executor_path_in_production.py'
        assert is_whitelisted(path)

    def test_no_finding_from_verb_chain_analyzer(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts' / '_analyze_verb_chains.py'
        _write_py(
            py,
            '# Verb chain scanner\nINVOCATION_RE = r"python3 .plan/execute-script.py"\n',
        )
        findings = analyze_executor_path_in_production(mp)
        assert findings == []


# ===========================================================================
# Fixture c: non-whitelisted production script — finding with category production_script
# ===========================================================================


class TestProductionScriptFinding:
    """Non-whitelisted production scripts emit a finding."""

    def test_production_script_finding(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'my-bundle' / 'skills' / 'my-skill' / 'scripts' / 'do_work.py'
        _write_py(
            py,
            '# Production script\nimport subprocess\n'
            'result = subprocess.run(["python3", ".plan/execute-script.py", "foo:bar:baz"])\n',
        )
        findings = analyze_executor_path_in_production(mp)
        assert len(findings) >= 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['category'] == 'production_script'
        assert isinstance(f['line'], int)
        assert f['line'] >= 1
        assert '.plan/execute-script.py' in f['snippet']

    def test_finding_shape(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / 'runner.py'
        _write_py(py, 'cmd = ".plan/execute-script.py "\n')
        findings = analyze_executor_path_in_production(mp)
        assert findings
        f = findings[0]
        for key in ('rule_id', 'file', 'line', 'category', 'snippet'):
            assert key in f


# ===========================================================================
# Helper-based compliance: get_executor_path() callers are COMPLIANT
# ===========================================================================


class TestHelperBasedCompliance:
    """Production code that adopts ``file_ops.get_executor_path()`` is COMPLIANT.

    The detection literal is RETAINED — a file embedding the executor path
    WITHOUT adopting the helper is still flagged (see
    :class:`TestProductionScriptFinding`). A file that references the helper is
    treated as COMPLIANT even when it still contains a residual
    ``.plan/execute-script.py`` literal (docstring/comment/error-message
    reference or a defensive fallback string).
    """

    def test_helper_caller_with_residual_literal_is_compliant(self, tmp_path: Path) -> None:
        # A production script that imports + calls get_executor_path() but also
        # keeps the literal in a docstring/fallback — must NOT be flagged.
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'my-bundle' / 'skills' / 'my-skill' / 'scripts' / 'runner.py'
        _write_py(
            py,
            '"""Invoked via the executor proxy: python3 .plan/execute-script.py."""\n'
            'from file_ops import get_executor_path\n'
            'executor = get_executor_path()\n'
            'fallback = str(executor) if executor else ".plan/execute-script.py"\n',
        )
        findings = analyze_executor_path_in_production(mp)
        assert findings == []

    def test_helper_definition_site_is_compliant(self, tmp_path: Path) -> None:
        # The helper-definition site itself (file_ops.py defining
        # get_executor_path) keeps the literal in docstrings; it is COMPLIANT
        # because it references the helper name.
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'plan-marshall' / 'skills' / 'tools-file-ops' / 'scripts' / 'file_ops.py'
        _write_py(
            py,
            'def get_executor_path():\n'
            '    """Return the canonical path to .plan/execute-script.py."""\n'
            "    return root / '.plan' / 'execute-script.py'\n",
        )
        findings = analyze_executor_path_in_production(mp)
        assert findings == []

    def test_old_hardcoded_form_without_helper_still_flagged(self, tmp_path: Path) -> None:
        # A production script that embeds the literal WITHOUT adopting the
        # helper is still flagged — the detection literal is RETAINED.
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'my-bundle' / 'skills' / 'my-skill' / 'scripts' / 'legacy.py'
        _write_py(
            py,
            '# Legacy: hardcoded executor path, no helper adoption\n'
            "executor = Path.cwd() / '.plan/execute-script.py'\n",
        )
        findings = analyze_executor_path_in_production(mp)
        assert len(findings) >= 1
        assert findings[0]['category'] == 'production_script'
        assert '.plan/execute-script.py' in findings[0]['snippet']


# ===========================================================================
# Fixture d: test assertion — finding with category test_assertion
# ===========================================================================


class TestTestAssertionFinding:
    """Occurrences inside test directories are categorized as test_assertion."""

    def test_test_file_category(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # A test file under bundles/...
        py = mp / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / 'test_runner.py'
        _write_py(
            py,
            '# Test file\nassert ".plan/execute-script.py" in captured_args\n',
        )
        findings = analyze_executor_path_in_production(mp)
        assert len(findings) >= 1
        assert any(f['category'] == 'test_assertion' for f in findings)


# ===========================================================================
# End-to-end: no findings on clean marketplace
# ===========================================================================


class TestCleanMarketplace:
    """Marketplace without any executor path references produces no findings."""

    def test_no_findings_when_clean(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = mp / 'bundles' / 'b1' / 'skills' / 's1' / 'scripts' / 'clean.py'
        _write_py(py, '# No executor references\ndef do_work():\n    pass\n')
        findings = analyze_executor_path_in_production(mp)
        assert findings == []

    def test_empty_bundles(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        findings = analyze_executor_path_in_production(mp)
        assert findings == []

    def test_nonexistent_marketplace(self, tmp_path: Path) -> None:
        mp = tmp_path / 'does-not-exist'
        findings = analyze_executor_path_in_production(mp)
        assert findings == []
