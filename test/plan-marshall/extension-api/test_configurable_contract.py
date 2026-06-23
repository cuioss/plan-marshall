#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for configurable_contract.py — the step-owned ``configurable``
frontmatter contract parser.

Covers the four task-required surfaces:

- valid declarations parse cleanly (``parse_configurable`` + ``resolve_step_defaults``);
- every malformed-declaration case raises a loud ``ValueError`` (missing key,
  missing default, missing description, empty description, non-string types,
  duplicate key, no frontmatter, no/empty ``configurable:`` block, file absent);
- scalar coercion of declared defaults (bool / int / float / null / quoted);
- ``resolve_step_doc_path`` resolution for ``default:`` and ``project:`` step ids;
- the CLI diagnostic surface (exit-code + TOON envelope, stderr-on-error).
"""

import pytest

# conftest.py sets up the executor PYTHONPATH so the sibling script module
# (configurable_contract) and the shared test infrastructure (conftest) import
# directly.
from configurable_contract import (  # type: ignore[import-not-found]
    parse_configurable,
    resolve_step_defaults,
    resolve_step_doc_path,
)
from conftest import create_temp_file, get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'extension-api', 'configurable_contract.py')


def _doc(configurable_block: str, *, leading: str = 'name: demo\norder: 10') -> str:
    """Build a step body doc with a ``---``-fenced frontmatter block."""
    return f'---\n{leading}\n{configurable_block}\n---\n\n# Body\n\nProse.\n'


# =============================================================================
# Valid declarations — parse cleanly
# =============================================================================


class TestValidDeclarations:
    """A well-formed configurable block parses to the expected schema."""

    def test_single_entry_full_schema(self):
        """A single complete entry yields default + description."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: touched_file_cleanup\n'
                '    default: new_code_only\n'
                '    description: Which surface the success criterion covers.'
            ),
            suffix='.md',
        )
        try:
            schema = parse_configurable(doc)
        finally:
            doc.unlink()
        assert schema == {
            'touched_file_cleanup': {
                'default': 'new_code_only',
                'description': 'Which surface the success criterion covers.',
            }
        }

    def test_multiple_entries_preserve_each_key(self):
        """Every declared entry surfaces as its own schema key."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: touched_file_cleanup\n'
                '    default: new_code_only\n'
                '    description: First param.\n'
                '  - key: do_transition\n'
                '    default: false\n'
                '    description: Second param.\n'
                '  - key: ce_wait_timeout_seconds\n'
                '    default: 600\n'
                '    description: Third param.'
            ),
            suffix='.md',
        )
        try:
            schema = parse_configurable(doc)
        finally:
            doc.unlink()
        assert set(schema) == {
            'touched_file_cleanup',
            'do_transition',
            'ce_wait_timeout_seconds',
        }
        assert schema['do_transition']['default'] is False
        assert schema['ce_wait_timeout_seconds']['default'] == 600

    def test_comments_and_blank_lines_ignored(self):
        """Comment and blank lines inside the block do not break parsing."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  # a leading comment\n'
                '\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: A param.'
            ),
            suffix='.md',
        )
        try:
            schema = parse_configurable(doc)
        finally:
            doc.unlink()
        assert schema == {'foo': {'default': 'bar', 'description': 'A param.'}}

    def test_block_terminates_at_next_top_level_key(self):
        """A top-level key after the block terminates it without leaking."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: A param.\n'
                'trailing_key: ignored'
            ),
            suffix='.md',
        )
        try:
            schema = parse_configurable(doc)
        finally:
            doc.unlink()
        assert list(schema) == ['foo']


# =============================================================================
# resolve_step_defaults — projection to defaults
# =============================================================================


class TestResolveStepDefaults:
    """resolve_step_defaults projects each entry to just its default value."""

    def test_resolve_defaults_for_project_step(self, tmp_path, monkeypatch):
        """A project: step resolves to .claude/skills/{name}/SKILL.md."""
        skill_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-demo'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            _doc(
                'configurable:\n'
                '  - key: enabled\n'
                '    default: true\n'
                '    description: Toggle.\n'
                '  - key: limit\n'
                '    default: 7\n'
                '    description: Bound.',
                leading='name: finalize-step-demo\norder: 50',
            ),
            encoding='utf-8',
        )
        import configurable_contract as cc

        monkeypatch.setattr(cc, '_repo_root', lambda: tmp_path)
        defaults = resolve_step_defaults('project:finalize-step-demo')
        assert defaults == {'enabled': True, 'limit': 7}


# =============================================================================
# Scalar coercion of declared defaults
# =============================================================================


class TestScalarCoercion:
    """The ``default`` scalar coerces to the right Python JSON-scalar type."""

    @pytest.mark.parametrize(
        ('raw_default', 'expected'),
        [
            ('true', True),
            ('false', False),
            ('null', None),
            ('~', None),
            ('600', 600),
            ('1.5', 1.5),
            ('"quoted string"', 'quoted string'),
            ("'single quoted'", 'single quoted'),
            ('plain_string', 'plain_string'),
        ],
    )
    def test_default_scalar_coercion(self, raw_default, expected):
        """Each scalar form coerces to its expected Python value."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: param\n'
                f'    default: {raw_default}\n'
                '    description: A param.'
            ),
            suffix='.md',
        )
        try:
            schema = parse_configurable(doc)
        finally:
            doc.unlink()
        assert schema['param']['default'] == expected
        assert type(schema['param']['default']) is type(expected)


# =============================================================================
# Malformed declarations — fail loud on every case
# =============================================================================


class TestMalformedDeclarations:
    """Every malformed-declaration case raises ValueError (no silent fallback)."""

    def test_file_not_found(self, tmp_path):
        """A non-existent body doc raises ValueError."""
        with pytest.raises(ValueError, match='step body doc not found'):
            parse_configurable(tmp_path / 'does-not-exist.md')

    def test_no_frontmatter_fence(self):
        """A doc with no '---' frontmatter fence raises ValueError."""
        doc = create_temp_file('# No frontmatter here\n\nJust prose.', suffix='.md')
        try:
            with pytest.raises(ValueError, match="no '---'-fenced frontmatter"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_unterminated_frontmatter(self):
        """An opening fence with no closing fence raises ValueError."""
        doc = create_temp_file('---\nname: demo\nconfigurable:\n  - key: x\n', suffix='.md')
        try:
            with pytest.raises(ValueError, match="no '---'-fenced frontmatter"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_no_configurable_block(self):
        """Frontmatter without a configurable: block raises ValueError."""
        doc = create_temp_file('---\nname: demo\norder: 10\n---\n\n# Body\n', suffix='.md')
        try:
            with pytest.raises(ValueError, match="declares no 'configurable:'"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_empty_configurable_block(self):
        """A configurable: block with no entries raises ValueError."""
        doc = create_temp_file(
            '---\nname: demo\norder: 10\nconfigurable:\n---\n\n# Body\n', suffix='.md'
        )
        try:
            with pytest.raises(ValueError, match="'configurable:' block is empty"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_missing_key_subfield(self):
        """An entry missing 'key' raises ValueError naming 'key'."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - default: bar\n'
                '    description: A param.'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match="missing required sub-field 'key'"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_missing_default_subfield(self):
        """An entry missing 'default' raises ValueError naming 'default'."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    description: A param.'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match="missing required sub-field 'default'"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_missing_description_subfield(self):
        """An entry missing 'description' raises ValueError naming 'description'."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match="missing required sub-field 'description'"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_empty_description(self):
        """An entry with an empty 'description' raises ValueError."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: ""'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match='empty'):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_non_string_key(self):
        """A numeric (non-string) 'key' raises ValueError."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: 42\n'
                '    default: bar\n'
                '    description: A param.'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match="'key' must be a string"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_non_string_description(self):
        """A numeric (non-string) 'description' raises ValueError."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: 99'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match="'description' must be a string"):
                parse_configurable(doc)
        finally:
            doc.unlink()

    def test_duplicate_key(self):
        """A key declared twice raises ValueError naming the duplicate."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    default: a\n'
                '    description: First.\n'
                '  - key: foo\n'
                '    default: b\n'
                '    description: Second.'
            ),
            suffix='.md',
        )
        try:
            with pytest.raises(ValueError, match="duplicate key 'foo'"):
                parse_configurable(doc)
        finally:
            doc.unlink()


# =============================================================================
# resolve_step_doc_path — body-doc resolution
# =============================================================================


class TestResolveStepDocPath:
    """resolve_step_doc_path maps a step id to its body-doc path."""

    def test_project_prefix_maps_to_claude_skills(self, tmp_path, monkeypatch):
        """A project: step resolves under .claude/skills/{name}/SKILL.md."""
        import configurable_contract as cc

        monkeypatch.setattr(cc, '_repo_root', lambda: tmp_path)
        path = resolve_step_doc_path('project:finalize-step-demo')
        assert path == tmp_path / '.claude' / 'skills' / 'finalize-step-demo' / 'SKILL.md'

    def test_default_prefix_prefers_workflow_then_standards(self, tmp_path, monkeypatch):
        """A built-in step prefers workflow/{name}.md, falling back to standards/."""
        import configurable_contract as cc

        skill_dir = tmp_path / 'phase-6-finalize'
        (skill_dir / 'workflow').mkdir(parents=True)
        (skill_dir / 'standards').mkdir(parents=True)
        monkeypatch.setattr(cc, '_phase_6_skill_dir', lambda: skill_dir)

        # Only standards/ exists -> resolves to standards/.
        (skill_dir / 'standards' / 'branch-cleanup.md').write_text('x', encoding='utf-8')
        assert resolve_step_doc_path('default:branch-cleanup') == (
            skill_dir / 'standards' / 'branch-cleanup.md'
        )

        # workflow/ exists -> wins over standards/.
        (skill_dir / 'workflow' / 'branch-cleanup.md').write_text('x', encoding='utf-8')
        assert resolve_step_doc_path('default:branch-cleanup') == (
            skill_dir / 'workflow' / 'branch-cleanup.md'
        )

    def test_missing_built_in_returns_preferred_workflow_path(self, tmp_path, monkeypatch):
        """When neither body doc exists, the preferred workflow/ path is returned."""
        import configurable_contract as cc

        skill_dir = tmp_path / 'phase-6-finalize'
        monkeypatch.setattr(cc, '_phase_6_skill_dir', lambda: skill_dir)
        assert resolve_step_doc_path('default:absent') == (
            skill_dir / 'workflow' / 'absent.md'
        )


# =============================================================================
# CLI diagnostic surface — exit codes + TOON envelope
# =============================================================================


class TestCli:
    """The CLI emits TOON on success (exit 0) and an error TOON on stderr (exit 1)."""

    def test_parse_success_emits_params_toon(self):
        """parse on a valid doc exits 0 and emits the params rows."""
        doc = create_temp_file(
            _doc(
                'configurable:\n'
                '  - key: foo\n'
                '    default: bar\n'
                '    description: A param.'
            ),
            suffix='.md',
        )
        try:
            result = run_script(SCRIPT_PATH, 'parse', '--path', str(doc))
        finally:
            doc.unlink()
        assert result.returncode == 0, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['params'][0]['key'] == 'foo'

    def test_parse_malformed_exits_1_with_error_on_stderr(self):
        """parse on a malformed doc exits 1 with an error TOON on stderr."""
        doc = create_temp_file('# no frontmatter', suffix='.md')
        try:
            result = run_script(SCRIPT_PATH, 'parse', '--path', str(doc))
        finally:
            doc.unlink()
        assert result.returncode == 1
        assert 'status: error' in result.stderr
        assert "no '---'-fenced frontmatter" in result.stderr

    def test_missing_subcommand_argparse_rejection(self):
        """Invoking with no subcommand is an argparse rejection (exit 2)."""
        result = run_script(SCRIPT_PATH)
        assert result.returncode == 2
