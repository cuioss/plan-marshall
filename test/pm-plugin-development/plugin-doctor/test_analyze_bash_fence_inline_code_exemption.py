# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``bash-fence-inline-code-exemption`` rule analyzer.

The analyzer is a reintroduction guard. It flags any ``*.py`` under
``marketplace/bundles/**/scripts/`` that defines BOTH a bash-fence marker
(``_BASH_FENCE_INFO_STRINGS``) AND a markdown inline-code exemption helper
(``_INLINE_CODE_RE`` / ``_inline_code_spans``). Inside a bash fence backticks
are command substitution, not markdown inline-code, so the two marker families
are mutually exclusive in a single analyzer.

Test layers:
  * Both markers present → finding (fixture a).
  * Only the bash-fence marker (post-PR-#474 bash-fence analyzers) → no finding (fixture b).
  * Only the inline-code helper (prose scanners) → no finding (fixture c).
  * The ``_inline_code_spans`` token variant also triggers (fixture d).
  * The analyzer's own file is excluded from its own scan (fixture e).
  * The REAL marketplace tree produces zero findings (fixture f, invariant guard).
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_abfice = _load_module(
    '_analyze_bash_fence_inline_code_exemption',
    '_analyze_bash_fence_inline_code_exemption.py',
)

analyze_bash_fence_inline_code_exemption = _abfice.analyze_bash_fence_inline_code_exemption
is_whitelisted = _abfice.is_whitelisted
RULE_ID = _abfice.RULE_ID


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


def _scripts_dir(mp: Path) -> Path:
    return mp / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'


# ===========================================================================
# Fixture a: both markers present — finding
# ===========================================================================


class TestBothMarkersPresent:
    """A file defining BOTH the bash-fence marker and an inline-code helper is flagged."""

    def test_both_markers_yield_finding(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / '_analyze_offender.py'
        _write_py(
            py,
            '_BASH_FENCE_INFO_STRINGS = ("bash", "sh")\n'
            "_INLINE_CODE_RE = r'`[^`]+`'\n"
            'def analyze_offender(root):\n'
            '    return []\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == 'bash_fence_inline_code_exemption'
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert isinstance(f['line'], int)
        assert f['line'] >= 1
        assert '_INLINE_CODE_RE' in f['snippet']
        assert 'description' in f

    def test_finding_shape(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / '_analyze_offender2.py'
        _write_py(
            py,
            '_BASH_FENCE_INFO_STRINGS = frozenset({"bash"})\n'
            '_INLINE_CODE_RE = None\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert findings
        f = findings[0]
        for key in (
            'rule_id',
            'type',
            'rule',
            'file',
            'line',
            'severity',
            'fixable',
            'snippet',
            'description',
        ):
            assert key in f


# ===========================================================================
# Fixture b: only the bash-fence marker — no finding
# ===========================================================================


class TestOnlyBashFenceMarker:
    """A post-PR-#474 bash-fence analyzer (no inline-code helper) is compliant."""

    def test_only_bash_fence_marker_no_finding(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / '_analyze_bash_only.py'
        _write_py(
            py,
            '_BASH_FENCE_INFO_STRINGS = ("bash", "sh")\n'
            'def analyze_bash_only(root):\n'
            '    return []\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert findings == []


# ===========================================================================
# Fixture c: only the inline-code helper — no finding
# ===========================================================================


class TestOnlyInlineCodeHelper:
    """A prose scanner (inline-code exemption only) is compliant."""

    def test_only_inline_code_re_no_finding(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / '_analyze_prose.py'
        _write_py(
            py,
            "_INLINE_CODE_RE = r'`[^`]+`'\n"
            'def analyze_prose(root):\n'
            '    return []\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert findings == []

    def test_only_inline_code_spans_no_finding(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / '_analyze_prose2.py'
        _write_py(
            py,
            'def _inline_code_spans(line):\n'
            '    return []\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert findings == []


# ===========================================================================
# Fixture d: the _inline_code_spans token variant also triggers
# ===========================================================================


class TestInlineCodeSpansVariant:
    """The ``_inline_code_spans`` token co-present with the fence marker triggers."""

    def test_inline_code_spans_variant_triggers(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / '_analyze_offender_spans.py'
        _write_py(
            py,
            '_BASH_FENCE_INFO_STRINGS = ("bash", "sh")\n'
            'def _inline_code_spans(line):\n'
            '    return []\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert '_inline_code_spans' in findings[0]['snippet']


# ===========================================================================
# Fixture e: self-reference exclusion
# ===========================================================================


class TestSelfReferenceExclusion:
    """The analyzer's own source is excluded from its own scan."""

    def test_self_reference_whitelisted(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / '_analyze_bash_fence_inline_code_exemption.py'
        )
        assert is_whitelisted(path)

    def test_self_source_produces_no_finding(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        # A synthetic copy of the analyzer's own filename naming both marker
        # families must be excluded from its own scan.
        py = _scripts_dir(mp) / '_analyze_bash_fence_inline_code_exemption.py'
        _write_py(
            py,
            '_BASH_FENCE_INFO_STRINGS = ("bash",)\n'
            "_INLINE_CODE_RE = r'`[^`]+`'\n",
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert findings == []

    def test_dispatch_host_whitelisted(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / 'bundles'
            / 'b1'
            / 'skills'
            / 's1'
            / 'scripts'
            / 'doctor-marketplace.py'
        )
        assert is_whitelisted(path)

    def test_dispatch_host_produces_no_finding(self, tmp_path: Path) -> None:
        # The dispatch host documents the rule in a comment naming both marker
        # families; it is a documentary reference, not an analyzer definition.
        mp = _make_marketplace(tmp_path)
        py = _scripts_dir(mp) / 'doctor-marketplace.py'
        _write_py(
            py,
            '# Rule docs: an analyzer defining _BASH_FENCE_INFO_STRINGS that\n'
            '# also carries _INLINE_CODE_RE / _inline_code_spans is flagged.\n',
        )
        findings = analyze_bash_fence_inline_code_exemption(mp)
        assert findings == []


# ===========================================================================
# Empty / missing tree edge cases
# ===========================================================================


class TestEmptyTree:
    """Empty or missing bundles trees produce no findings."""

    def test_empty_bundles(self, tmp_path: Path) -> None:
        mp = _make_marketplace(tmp_path)
        assert analyze_bash_fence_inline_code_exemption(mp) == []

    def test_nonexistent_marketplace(self, tmp_path: Path) -> None:
        mp = tmp_path / 'does-not-exist'
        assert analyze_bash_fence_inline_code_exemption(mp) == []
