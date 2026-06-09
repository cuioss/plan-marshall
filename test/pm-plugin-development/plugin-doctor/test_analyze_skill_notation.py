# ruff: noqa: I001, E402
"""Tests for the ``skill-notation-unresolved`` rule analyzer.

The analyzer scans marketplace markdown under every bundle's
``{skills,agents,commands}/`` subtrees for ``Skill: {bundle}:{skill}``
directive tokens and asserts that the referenced skill directory
``bundles/{bundle}/skills/{skill}/`` exists on disk. A directive whose target
skill directory is missing produces a finding — a ``Skill:`` directive that
does not resolve is a dead reference.

Only the two-segment bundle-prefixed form is validated, and only when the
first segment is a real on-disk bundle (a bundle directory carrying a
``.claude-plugin/plugin.json``). Bare single-segment directives and incidental
colon-joined tokens whose first segment is not a bundle are ignored.

Test layers:
  * Directive whose skill dir exists → no finding (positive case)
  * Directive whose skill dir is missing → one finding (negative case)
  * Boundary: non-bundle first segment ignored, three-segment executor
    notation not matched, duplicate directives deduped per line
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_asn = _load_module('_analyze_skill_notation', '_analyze_skill_notation.py')

analyze_skill_notation = _asn.analyze_skill_notation
RULE_ID = _asn.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace bundles tree.
# ---------------------------------------------------------------------------


def _make_bundle(tmp_path: Path, bundle: str) -> Path:
    """Create ``{bundle}/.claude-plugin/plugin.json`` so the bundle is "real"."""
    bundle_dir = tmp_path / bundle
    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / 'plugin.json').write_text('{}', encoding='utf-8')
    return bundle_dir


def _make_skill_dir(bundle_dir: Path, skill: str) -> None:
    """Create ``{bundle}/skills/{skill}/`` so the skill notation resolves."""
    (bundle_dir / 'skills' / skill).mkdir(parents=True, exist_ok=True)


def _write_skill_md(bundle_dir: Path, skill: str, body: str) -> Path:
    """Write ``{bundle}/skills/{skill}/SKILL.md`` with ``body`` and return path."""
    skill_dir = bundle_dir / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(body, encoding='utf-8')
    return md


# ===========================================================================
# Positive cases — directive whose skill dir exists → no finding.
# ===========================================================================


class TestDirectiveResolves:
    """A ``Skill:`` directive that resolves on disk produces no findings."""

    def test_resolving_directive_silent(self, tmp_path: Path) -> None:
        bundle = _make_bundle(tmp_path, 'my-bundle')
        _make_skill_dir(bundle, 'target-skill')
        _write_skill_md(
            bundle,
            'host-skill',
            'Load it:\n\nSkill: my-bundle:target-skill\n',
        )

        findings = analyze_skill_notation(tmp_path)

        assert findings == []

    def test_non_bundle_first_segment_ignored(self, tmp_path: Path) -> None:
        """A two-segment token whose first segment is not a real bundle is skipped."""
        bundle = _make_bundle(tmp_path, 'my-bundle')
        _write_skill_md(
            bundle,
            'host-skill',
            'Incidental token: Skill: not-a-bundle:something\n',
        )

        findings = analyze_skill_notation(tmp_path)

        assert findings == []

    def test_three_segment_executor_notation_not_matched(self, tmp_path: Path) -> None:
        """A three-segment executor notation is not a Skill directive."""
        bundle = _make_bundle(tmp_path, 'my-bundle')
        _make_skill_dir(bundle, 'manage-status')
        _write_skill_md(
            bundle,
            'host-skill',
            'Run: Skill: my-bundle:manage-status:manage-status read\n',
        )

        findings = analyze_skill_notation(tmp_path)

        # The directive regex bounds the skill segment with a non-`:` lookahead,
        # so the trailing `:manage-status` makes this an executor notation, not
        # a Skill directive — no finding regardless of skill-dir presence.
        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        findings = analyze_skill_notation(tmp_path)

        assert findings == []


# ===========================================================================
# Negative cases — directive whose skill dir is missing → one finding.
# ===========================================================================


class TestDirectiveUnresolved:
    """A ``Skill:`` directive that does not resolve produces one finding."""

    def test_missing_skill_dir_flagged(self, tmp_path: Path) -> None:
        bundle = _make_bundle(tmp_path, 'my-bundle')
        # target-skill dir is NOT created — the directive is a dead reference.
        md = _write_skill_md(
            bundle,
            'host-skill',
            'Load it:\n\nSkill: my-bundle:ghost-skill\n',
        )

        findings = analyze_skill_notation(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'error'
        assert finding['fixable'] is False
        assert finding['file'] == str(md)
        assert finding['line'] == 3
        details = finding['details']
        assert details['notation'] == 'my-bundle:ghost-skill'
        assert details['bundle'] == 'my-bundle'
        assert details['skill'] == 'ghost-skill'
        assert details['reason'] == 'skill_dir_missing'

    def test_duplicate_directive_on_same_line_deduped(self, tmp_path: Path) -> None:
        """Two identical directives on one line produce a single finding."""
        bundle = _make_bundle(tmp_path, 'my-bundle')
        _write_skill_md(
            bundle,
            'host-skill',
            'Skill: my-bundle:ghost-skill and again Skill: my-bundle:ghost-skill\n',
        )

        findings = analyze_skill_notation(tmp_path)

        assert len(findings) == 1

    def test_directive_in_agent_markdown_flagged(self, tmp_path: Path) -> None:
        """Markdown under ``agents/`` is scanned in addition to ``skills/``."""
        bundle = _make_bundle(tmp_path, 'my-bundle')
        agents_dir = bundle / 'agents'
        agents_dir.mkdir(parents=True)
        (agents_dir / 'my-agent.md').write_text(
            'Skill: my-bundle:ghost-skill\n', encoding='utf-8'
        )

        findings = analyze_skill_notation(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['notation'] == 'my-bundle:ghost-skill'

    def test_multiple_unresolved_directives_each_flagged(self, tmp_path: Path) -> None:
        bundle = _make_bundle(tmp_path, 'my-bundle')
        _make_skill_dir(bundle, 'real-skill')
        _write_skill_md(
            bundle,
            'host-skill',
            'Skill: my-bundle:real-skill\n'
            'Skill: my-bundle:ghost-one\n'
            'Skill: my-bundle:ghost-two\n',
        )

        findings = analyze_skill_notation(tmp_path)

        assert len(findings) == 2
        skills = {f['details']['skill'] for f in findings}
        assert skills == {'ghost-one', 'ghost-two'}


# ===========================================================================
# Boundary cases — scope of the markdown scan.
# ===========================================================================


class TestScanScope:
    """Only markdown under a real bundle's component subtrees is scanned."""

    def test_non_bundle_directory_not_scanned(self, tmp_path: Path) -> None:
        """A directory without a plugin.json is not a bundle — its md is skipped."""
        # No .claude-plugin/plugin.json — this is not a real bundle.
        stray = tmp_path / 'not-a-bundle' / 'skills' / 'host'
        stray.mkdir(parents=True)
        (stray / 'SKILL.md').write_text(
            'Skill: not-a-bundle:ghost-skill\n', encoding='utf-8'
        )

        findings = analyze_skill_notation(tmp_path)

        assert findings == []
