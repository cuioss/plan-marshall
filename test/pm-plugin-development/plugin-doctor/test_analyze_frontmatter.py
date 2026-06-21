# ruff: noqa: I001, E402
"""Tests for the ``recipe-missing-implements`` rule analyzer.

Recipe skills are extension-point implementors: every ``recipe-*`` skill must
declare ``implements: plan-marshall:extension-api/standards/ext-point-recipe``
in its ``SKILL.md`` frontmatter so the extension-api discovery layer can
resolve it as a recipe provider. A ``recipe-*`` skill whose ``SKILL.md`` omits
``implements:`` (or declares a divergent value) is invisible to recipe
discovery — this analyzer flags that gap.

Two tree families are scanned:
  * ``marketplace_root/{bundle}/skills/recipe-*/SKILL.md``
  * ``recipe-*/SKILL.md`` under every project-local-skill root the active
    target's layout op reports (the Claude ``.claude/skills`` tree, or the
    OpenCode layout), resolved via ``_doctor_shared.resolve_project_skill_trees``.

Test layers:
  * Recipe skill with the canonical ``implements:`` → no finding (positive)
  * Recipe skill missing ``implements:`` → one finding (negative)
  * Recipe skill with a divergent ``implements:`` → one finding (boundary)
  * Non-recipe skills and the project-local skill trees (Claude default + a
    forced multi-root OpenCode-style layout)
"""

import pytest
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ds = _load_module('_doctor_shared', '_doctor_shared.py')
_af = _load_module('_analyze_frontmatter', '_analyze_frontmatter.py')

analyze_frontmatter = _af.analyze_frontmatter
RULE_ID = _af.RULE_ID
_REQUIRED = _af._REQUIRED_IMPLEMENTS


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace/.claude tree.
# ---------------------------------------------------------------------------


def _bundles_root(tmp_path: Path) -> Path:
    """Return the ``marketplace/bundles`` root, created under ``tmp_path``.

    The analyzer derives the project-local ``.claude/skills`` tree as
    ``marketplace_root.parent.parent``, so the bundles root MUST live two
    levels under the repo root (``tmp_path``) for that derivation to land at
    ``tmp_path/.claude/skills``.
    """
    root = tmp_path / 'marketplace' / 'bundles'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_recipe_skill(bundles_root: Path, bundle: str, skill: str, body: str) -> Path:
    """Write ``{bundle}/skills/{skill}/SKILL.md`` and return the SKILL.md path."""
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(body, encoding='utf-8')
    return md


def _write_claude_recipe_skill(tmp_path: Path, skill: str, body: str) -> Path:
    """Write ``{repo_root}/.claude/skills/{skill}/SKILL.md`` and return its path."""
    skill_dir = tmp_path / '.claude' / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(body, encoding='utf-8')
    return md


def _frontmatter(implements: str | None) -> str:
    """Build a minimal SKILL.md body, optionally declaring ``implements:``."""
    lines = ['---', 'name: recipe-thing', 'description: A recipe']
    if implements is not None:
        lines.append(f'implements: {implements}')
    lines.append('---')
    lines.append('')
    lines.append('# Recipe Thing')
    return '\n'.join(lines) + '\n'


# ===========================================================================
# Positive cases — canonical implements: present → no finding.
# ===========================================================================


class TestImplementsPresent:
    """A recipe skill declaring the canonical ``implements:`` is silent."""

    def test_canonical_implements_silent(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        _write_recipe_skill(root, 'my-bundle', 'recipe-foo', _frontmatter(_REQUIRED))

        findings = analyze_frontmatter(root)

        assert findings == []

    def test_quoted_implements_value_accepted(self, tmp_path: Path) -> None:
        """A double-quoted ``implements:`` scalar is accepted after quote-strip."""
        root = _bundles_root(tmp_path)
        _write_recipe_skill(root, 'my-bundle', 'recipe-foo', _frontmatter(f'"{_REQUIRED}"'))

        findings = analyze_frontmatter(root)

        assert findings == []

    def test_non_recipe_skill_not_scanned(self, tmp_path: Path) -> None:
        """A skill whose name is not ``recipe-*`` is out of scope."""
        root = _bundles_root(tmp_path)
        # No implements: at all, but the dir is `manage-foo`, not `recipe-*`.
        _write_recipe_skill(root, 'my-bundle', 'manage-foo', _frontmatter(None))

        findings = analyze_frontmatter(root)

        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)

        findings = analyze_frontmatter(root)

        assert findings == []


# ===========================================================================
# Negative cases — missing implements: → one finding.
# ===========================================================================


class TestImplementsMissing:
    """A recipe skill lacking ``implements:`` produces one finding."""

    def test_missing_implements_flagged(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        md = _write_recipe_skill(root, 'my-bundle', 'recipe-foo', _frontmatter(None))

        findings = analyze_frontmatter(root)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'error'
        assert finding['fixable'] is False
        assert finding['file'] == str(md)
        details = finding['details']
        assert details['skill'] == 'recipe-foo'
        assert details['required_implements'] == _REQUIRED
        assert details['reason'] == 'implements_missing'
        assert 'declared_implements' not in details

    def test_recipe_without_skill_md_is_exempt(self, tmp_path: Path) -> None:
        """A ``recipe-*`` directory with no SKILL.md is not this rule's concern."""
        root = _bundles_root(tmp_path)
        (root / 'my-bundle' / 'skills' / 'recipe-empty').mkdir(parents=True)

        findings = analyze_frontmatter(root)

        assert findings == []

    def test_multiple_missing_each_flagged(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        _write_recipe_skill(root, 'my-bundle', 'recipe-a', _frontmatter(None))
        _write_recipe_skill(root, 'my-bundle', 'recipe-b', _frontmatter(None))
        _write_recipe_skill(root, 'my-bundle', 'recipe-c', _frontmatter(_REQUIRED))

        findings = analyze_frontmatter(root)

        assert len(findings) == 2
        skills = {f['details']['skill'] for f in findings}
        assert skills == {'recipe-a', 'recipe-b'}


# ===========================================================================
# Boundary cases — divergent implements: and project-local .claude tree.
# ===========================================================================


class TestImplementsDivergent:
    """A divergent ``implements:`` value produces a finding with the declared value."""

    def test_divergent_implements_flagged(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        md = _write_recipe_skill(
            root, 'my-bundle', 'recipe-foo', _frontmatter('plan-marshall:wrong/notation')
        )

        findings = analyze_frontmatter(root)

        assert len(findings) == 1
        details = findings[0]['details']
        assert details['reason'] == 'implements_divergent'
        assert details['declared_implements'] == 'plan-marshall:wrong/notation'
        assert findings[0]['file'] == str(md)


class TestClaudeSkillsTree:
    """The project-local ``.claude/skills/recipe-*`` tree is scanned too."""

    def test_claude_recipe_missing_implements_flagged(self, tmp_path: Path) -> None:
        # Force the bundles root to exist (analyzer iterates it first).
        _bundles_root(tmp_path)
        root = tmp_path / 'marketplace' / 'bundles'
        md = _write_claude_recipe_skill(tmp_path, 'recipe-local', _frontmatter(None))

        findings = analyze_frontmatter(root)

        assert len(findings) == 1
        assert findings[0]['file'] == str(md)
        assert findings[0]['details']['skill'] == 'recipe-local'

    def test_claude_recipe_with_canonical_implements_silent(self, tmp_path: Path) -> None:
        _bundles_root(tmp_path)
        root = tmp_path / 'marketplace' / 'bundles'
        _write_claude_recipe_skill(tmp_path, 'recipe-local', _frontmatter(_REQUIRED))

        findings = analyze_frontmatter(root)

        assert findings == []


class TestMultiRootLayout:
    """Both project-local-skill roots are scanned (target-aware, OpenCode-style).

    On OpenCode the layout op reports a multi-root list. The analyzer resolves
    its project-local trees through ``_doctor_shared.resolve_project_skill_trees``,
    which routes through ``marketplace_paths.get_project_skill_roots``. Forcing
    that helper to a two-root layout proves the analyzer scans EVERY reported
    root, not just the single Claude ``.claude/skills`` tree.
    """

    def test_recipe_under_each_root_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = _bundles_root(tmp_path)
        claude_recipe = tmp_path / '.claude' / 'skills' / 'recipe-claude'
        opencode_recipe = tmp_path / '.opencode' / 'skill' / 'recipe-opencode'
        for skill_dir in (claude_recipe, opencode_recipe):
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / 'SKILL.md').write_text(_frontmatter(None), encoding='utf-8')

        # Force the layout op to report both roots (mirrors the OpenCode
        # executor's multi-root discovery). resolve_project_skill_trees anchors
        # relative roots at the repo root (tmp_path here).
        monkeypatch.setattr(_ds, 'get_project_skill_roots', lambda: ('.claude/skills', '.opencode/skill'))

        findings = analyze_frontmatter(root)

        flagged = {f['details']['skill'] for f in findings}
        assert flagged == {'recipe-claude', 'recipe-opencode'}, f'both roots should be scanned, got {flagged}'
