# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``skill-missing-mode`` rule analyzer.

Every skill declares its execution archetype via the ``mode:`` frontmatter
field — the single, authoritative signal for how the skill is consumed. The
value MUST be exactly one of the closed enum
``{knowledge, workflow, script-executor, manifest}``. A skill whose
``SKILL.md`` omits ``mode:`` (or declares a value outside that enum) is not
classifiable by archetype-aware consumers — this analyzer flags that gap.

Two trees are scanned (no allowlist; every skill carrying a ``SKILL.md`` is in
scope):
  * ``marketplace_root/{bundle}/skills/{skill}/SKILL.md``
  * ``{repo_root}/.claude/skills/{skill}/SKILL.md`` where the repo root is
    ``marketplace_root.parent.parent`` (``marketplace_root`` is
    ``marketplace/bundles``).

Test layers:
  * Skill with a valid ``mode:`` → no finding (positive)
  * Skill missing ``mode:`` → one finding, ``reason == mode_missing`` (negative)
  * Skill with an out-of-enum ``mode:`` → one finding, ``reason == mode_invalid``
  * Edge cases — empty frontmatter, no frontmatter at all
  * The project-local ``.claude/skills`` tree
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_asm = _load_module('_analyze_skill_mode', '_analyze_skill_mode.py')

analyze_skill_mode = _asm.analyze_skill_mode
RULE_ID = _asm.RULE_ID
_VALID_MODES = _asm._VALID_MODES


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


def _write_skill(bundles_root: Path, bundle: str, skill: str, body: str) -> Path:
    """Write ``{bundle}/skills/{skill}/SKILL.md`` and return the SKILL.md path."""
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(body, encoding='utf-8')
    return md


def _write_claude_skill(tmp_path: Path, skill: str, body: str) -> Path:
    """Write ``{repo_root}/.claude/skills/{skill}/SKILL.md`` and return its path."""
    skill_dir = tmp_path / '.claude' / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(body, encoding='utf-8')
    return md


def _frontmatter(mode: str | None) -> str:
    """Build a minimal SKILL.md body, optionally declaring ``mode:``."""
    lines = ['---', 'name: some-skill', 'description: A skill']
    if mode is not None:
        lines.append(f'mode: {mode}')
    lines.append('---')
    lines.append('')
    lines.append('# Some Skill')
    return '\n'.join(lines) + '\n'


# ===========================================================================
# Positive cases — valid mode: present → no finding.
# ===========================================================================


class TestModePresent:
    """A skill declaring a valid ``mode:`` is silent."""

    def test_valid_mode_silent(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        _write_skill(root, 'my-bundle', 'manage-foo', _frontmatter('knowledge'))

        findings = analyze_skill_mode(root)

        assert findings == []

    def test_every_enum_member_silent(self, tmp_path: Path) -> None:
        """Each member of the closed enum is accepted with no finding."""
        root = _bundles_root(tmp_path)
        for index, mode in enumerate(sorted(_VALID_MODES)):
            _write_skill(root, 'my-bundle', f'skill-{index}', _frontmatter(mode))

        findings = analyze_skill_mode(root)

        assert findings == []

    def test_quoted_mode_value_accepted(self, tmp_path: Path) -> None:
        """A double-quoted ``mode:`` scalar is accepted after quote-strip."""
        root = _bundles_root(tmp_path)
        _write_skill(root, 'my-bundle', 'manage-foo', _frontmatter('"workflow"'))

        findings = analyze_skill_mode(root)

        assert findings == []

    def test_skill_without_skill_md_is_exempt(self, tmp_path: Path) -> None:
        """A skill directory with no SKILL.md is not this rule's concern."""
        root = _bundles_root(tmp_path)
        (root / 'my-bundle' / 'skills' / 'skill-empty').mkdir(parents=True)

        findings = analyze_skill_mode(root)

        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)

        findings = analyze_skill_mode(root)

        assert findings == []


# ===========================================================================
# Negative cases — missing mode: → one finding (reason: mode_missing).
# ===========================================================================


class TestModeMissing:
    """A skill lacking ``mode:`` produces one finding."""

    def test_missing_mode_flagged(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        md = _write_skill(root, 'my-bundle', 'manage-foo', _frontmatter(None))

        findings = analyze_skill_mode(root)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'error'
        assert finding['fixable'] is False
        assert finding['file'] == str(md)
        assert finding['line'] == 1
        details = finding['details']
        assert details['skill'] == 'manage-foo'
        assert details['valid_modes'] == sorted(_VALID_MODES)
        assert details['reason'] == 'mode_missing'
        assert 'declared_mode' not in details

    def test_multiple_missing_each_flagged(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        _write_skill(root, 'my-bundle', 'skill-a', _frontmatter(None))
        _write_skill(root, 'my-bundle', 'skill-b', _frontmatter(None))
        _write_skill(root, 'my-bundle', 'skill-c', _frontmatter('manifest'))

        findings = analyze_skill_mode(root)

        assert len(findings) == 2
        skills = {f['details']['skill'] for f in findings}
        assert skills == {'skill-a', 'skill-b'}


# ===========================================================================
# Boundary cases — out-of-enum mode: → one finding (reason: mode_invalid).
# ===========================================================================


class TestModeInvalid:
    """An out-of-enum ``mode:`` value produces a finding with the declared value."""

    def test_invalid_mode_flagged(self, tmp_path: Path) -> None:
        root = _bundles_root(tmp_path)
        md = _write_skill(root, 'my-bundle', 'manage-foo', _frontmatter('reference'))

        findings = analyze_skill_mode(root)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['severity'] == 'error'
        assert finding['file'] == str(md)
        details = finding['details']
        assert details['reason'] == 'mode_invalid'
        assert details['declared_mode'] == 'reference'
        assert details['valid_modes'] == sorted(_VALID_MODES)


# ===========================================================================
# Edge cases — empty frontmatter, no frontmatter at all.
# ===========================================================================


class TestFrontmatterEdges:
    """Frontmatter shape edge cases all classify as ``mode_missing``."""

    def test_empty_frontmatter_block_flagged(self, tmp_path: Path) -> None:
        """A SKILL.md with an empty ``---`` block has no ``mode:`` → flagged."""
        root = _bundles_root(tmp_path)
        body = '---\n---\n\n# Some Skill\n'
        md = _write_skill(root, 'my-bundle', 'manage-foo', body)

        findings = analyze_skill_mode(root)

        assert len(findings) == 1
        assert findings[0]['file'] == str(md)
        assert findings[0]['details']['reason'] == 'mode_missing'
        assert 'declared_mode' not in findings[0]['details']

    def test_no_frontmatter_at_all_flagged(self, tmp_path: Path) -> None:
        """A SKILL.md with no ``---`` fence has no parseable ``mode:`` → flagged."""
        root = _bundles_root(tmp_path)
        body = '# Some Skill\n\nProse with no frontmatter fence.\n'
        md = _write_skill(root, 'my-bundle', 'manage-foo', body)

        findings = analyze_skill_mode(root)

        assert len(findings) == 1
        assert findings[0]['file'] == str(md)
        assert findings[0]['details']['reason'] == 'mode_missing'

    def test_unterminated_frontmatter_flagged(self, tmp_path: Path) -> None:
        """An opening ``---`` with no closing fence is treated as no frontmatter."""
        root = _bundles_root(tmp_path)
        body = '---\nname: some-skill\nmode: knowledge\n\n# Some Skill\n'
        md = _write_skill(root, 'my-bundle', 'manage-foo', body)

        findings = analyze_skill_mode(root)

        # The closing ``---`` never appears, so the parser returns None and the
        # mode is considered absent.
        assert len(findings) == 1
        assert findings[0]['file'] == str(md)
        assert findings[0]['details']['reason'] == 'mode_missing'


# ===========================================================================
# Project-local .claude/skills tree is scanned too.
# ===========================================================================


class TestClaudeSkillsTree:
    """The project-local ``.claude/skills`` tree is scanned in full."""

    def test_claude_skill_missing_mode_flagged(self, tmp_path: Path) -> None:
        # Force the bundles root to exist (analyzer iterates it first).
        _bundles_root(tmp_path)
        root = tmp_path / 'marketplace' / 'bundles'
        md = _write_claude_skill(tmp_path, 'local-skill', _frontmatter(None))

        findings = analyze_skill_mode(root)

        assert len(findings) == 1
        assert findings[0]['file'] == str(md)
        assert findings[0]['details']['skill'] == 'local-skill'
        assert findings[0]['details']['reason'] == 'mode_missing'

    def test_claude_skill_with_valid_mode_silent(self, tmp_path: Path) -> None:
        _bundles_root(tmp_path)
        root = tmp_path / 'marketplace' / 'bundles'
        _write_claude_skill(tmp_path, 'local-skill', _frontmatter('script-executor'))

        findings = analyze_skill_mode(root)

        assert findings == []
