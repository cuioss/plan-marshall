# ruff: noqa: I001, E402
"""Tests for the ``metadata-field-undefined`` rule analyzer.

The analyzer performs a two-phase static check:
  Phase 1: Build an authoritative set of field names from
           ``set-metadata --key {field}`` invocations across the marketplace.
  Phase 2: Scan skill prose for backtick snake_case tokens near ``metadata``
           mentions and flag those not in the authoritative set.

Test layers:
  * Phase 1: ``build_authoritative_field_set`` — determinism, builtin fields,
    extraction from markdown.
  * Phase 2 — defined field reference: no finding emitted.
  * Phase 2 — undefined field reference: finding emitted.
  * Phase 2 — heuristic boundary: backtick token outside metadata context
    does NOT trigger.
  * End-to-end: ``analyze_metadata_field_validity`` wired through a minimal
    marketplace tree.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

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


_amfv = _load_module('_analyze_metadata_field_validity', '_analyze_metadata_field_validity.py')

analyze_metadata_field_validity = _amfv.analyze_metadata_field_validity
build_authoritative_field_set = _amfv.build_authoritative_field_set
scan_skill_for_undefined_fields = _amfv.scan_skill_for_undefined_fields
RULE_ID = _amfv.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_marketplace(tmp_path: Path) -> Path:
    """Create a ``marketplace/bundles/`` skeleton. Returns the marketplace root."""
    mp = tmp_path / 'marketplace'
    (mp / 'bundles').mkdir(parents=True)
    return mp


def _add_bundle_markdown(mp: Path, bundle: str, skill: str, filename: str, content: str) -> Path:
    """Write a markdown file inside a skill directory of the marketplace."""
    skill_dir = mp / 'bundles' / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / filename
    md.write_text(content, encoding='utf-8')
    return skill_dir


def _make_skill_md(skill_dir: Path, content: str) -> Path:
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


# ===========================================================================
# Phase 1: build_authoritative_field_set
# ===========================================================================


class TestBuildAuthoritativeFieldSet:
    """Phase 1: deterministic field-set construction."""

    def test_builtin_fields_always_present(self, tmp_path: Path) -> None:
        """Builtin fields like ``change_type`` are always in the set."""
        mp = _make_marketplace(tmp_path)
        result = build_authoritative_field_set(mp)
        assert 'change_type' in result
        assert 'worktree_path' in result
        assert 'use_worktree' in result
        assert 'confidence' in result

    def test_extracts_field_from_set_metadata_key(self, tmp_path: Path) -> None:
        """A ``set-metadata --key my_custom_field`` write is captured."""
        mp = _make_marketplace(tmp_path)
        skill_dir = _add_bundle_markdown(
            mp, 'my-bundle', 'my-skill', 'SKILL.md',
            'python3 .plan/execute-script.py foo:bar:baz set-metadata --key my_custom_field --value x\n',
        )
        result = build_authoritative_field_set(mp)
        assert 'my_custom_field' in result

    def test_deterministic_on_same_state(self, tmp_path: Path) -> None:
        """Two calls on the same marketplace state produce identical sets."""
        mp = _make_marketplace(tmp_path)
        _add_bundle_markdown(
            mp, 'b1', 's1', 'SKILL.md',
            'set-metadata --key alpha_field --value x\n',
        )
        first = build_authoritative_field_set(mp)
        second = build_authoritative_field_set(mp)
        assert first == second

    def test_empty_marketplace_returns_builtins(self, tmp_path: Path) -> None:
        """Empty marketplace directory still returns the builtin set."""
        mp = _make_marketplace(tmp_path)
        result = build_authoritative_field_set(mp)
        assert len(result) >= 10  # At least the builtin fields

    def test_nonexistent_root_returns_builtins(self, tmp_path: Path) -> None:
        """Non-existent marketplace root returns builtins only (no error)."""
        mp = tmp_path / 'nonexistent'
        result = build_authoritative_field_set(mp)
        assert 'change_type' in result


# ===========================================================================
# Phase 2: scan_skill_for_undefined_fields
# ===========================================================================


class TestScanSkillForUndefinedFields:
    """Phase 2: per-skill prose scanning."""

    def test_defined_field_reference_no_finding(self, tmp_path: Path) -> None:
        """A defined field name near metadata prose does not produce a finding."""
        authoritative = frozenset({'change_type', 'plan_id'})
        skill_dir = tmp_path / 'skill'
        (skill_dir / 'standards').mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            'The metadata field `change_type` controls the plan type.\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_undefined_fields(skill_dir, authoritative)
        assert findings == []

    def test_undefined_field_reference_finding_emitted(self, tmp_path: Path) -> None:
        """An undefined field name near metadata prose emits a finding."""
        authoritative = frozenset({'change_type', 'plan_id'})
        skill_dir = tmp_path / 'skill'
        (skill_dir / 'standards').mkdir(parents=True)
        _make_skill_md(
            skill_dir,
            'The metadata field `ghost_field_name` is used for tracking.\n',
        )
        findings = scan_skill_for_undefined_fields(skill_dir, authoritative)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['field_name'] == 'ghost_field_name'
        assert isinstance(f['line'], int)
        assert f['line'] >= 1
        assert 'file' in f
        assert 'narrative_context' in f

    def test_backtick_token_outside_metadata_context_not_flagged(self, tmp_path: Path) -> None:
        """A backtick snake_case token that does NOT appear near metadata prose is not flagged."""
        authoritative = frozenset({'change_type'})
        skill_dir = tmp_path / 'skill'
        (skill_dir / 'standards').mkdir(parents=True)
        _make_skill_md(
            skill_dir,
            # token appears far from any metadata mention
            '# Overview\n\nThis section discusses `unrelated_field_name` in a general context.\n'
            '\n\n\n\n\n\n\n\n'
            '# Metadata\n\nSee docs for details.\n',
        )
        findings = scan_skill_for_undefined_fields(skill_dir, authoritative)
        # `unrelated_field_name` is more than 3 lines away from the Metadata heading;
        # the heuristic should not fire on it.
        assert not any(f['field_name'] == 'unrelated_field_name' for f in findings)

    def test_short_token_not_flagged(self, tmp_path: Path) -> None:
        """Very short tokens (< 4 chars) inside inline code near metadata are ignored."""
        authoritative = frozenset({'change_type'})
        skill_dir = tmp_path / 'skill'
        (skill_dir / 'standards').mkdir(parents=True)
        _make_skill_md(
            skill_dir,
            'The set-metadata call uses `id` and `key` as params.\n',
        )
        findings = scan_skill_for_undefined_fields(skill_dir, authoritative)
        # 'id' and 'key' are < 4 chars — should not be flagged
        assert not any(f['field_name'] in ('id', 'key') for f in findings)

    def test_standards_subdir_also_scanned(self, tmp_path: Path) -> None:
        """Violations in standards/*.md are detected."""
        authoritative = frozenset({'change_type'})
        skill_dir = tmp_path / 'skill'
        standards_dir = skill_dir / 'standards'
        standards_dir.mkdir(parents=True)
        (standards_dir / 'workflow.md').write_text(
            'The set-metadata call writes `novel_field_xyz` for tracking.\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_undefined_fields(skill_dir, authoritative)
        assert any(f['field_name'] == 'novel_field_xyz' for f in findings)

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Each finding carries all required keys."""
        authoritative = frozenset()
        skill_dir = tmp_path / 'skill'
        (skill_dir / 'standards').mkdir(parents=True)
        _make_skill_md(
            skill_dir,
            'The metadata key `some_field_name` is required.\n',
        )
        findings = scan_skill_for_undefined_fields(skill_dir, authoritative)
        assert findings
        f = findings[0]
        for key in ('rule_id', 'file', 'line', 'field_name', 'narrative_context'):
            assert key in f, f'Missing key: {key}'


# ===========================================================================
# End-to-end: analyze_metadata_field_validity
# ===========================================================================


class TestAnalyzeMetadataFieldValidity:
    """End-to-end: wired through a minimal marketplace tree."""

    def test_no_findings_for_defined_fields(self, tmp_path: Path) -> None:
        """A skill that references only defined fields produces no findings."""
        mp = _make_marketplace(tmp_path)
        # Register the field
        _add_bundle_markdown(
            mp, 'b1', 's1', 'SKILL.md',
            'set-metadata --key my_registered_field --value x\n'
            'The metadata field `my_registered_field` controls something.\n',
        )
        findings = analyze_metadata_field_validity(mp)
        assert not any(f['field_name'] == 'my_registered_field' for f in findings)

    def test_finding_for_undefined_field(self, tmp_path: Path) -> None:
        """A skill that references an undefined field emits a finding."""
        mp = _make_marketplace(tmp_path)
        _add_bundle_markdown(
            mp, 'b1', 's1', 'SKILL.md',
            'The metadata field `absolutely_unknown_xyz` is used here.\n',
        )
        findings = analyze_metadata_field_validity(mp)
        assert any(f['field_name'] == 'absolutely_unknown_xyz' for f in findings)

    def test_empty_marketplace_no_crash(self, tmp_path: Path) -> None:
        """Empty marketplace does not crash."""
        mp = _make_marketplace(tmp_path)
        findings = analyze_metadata_field_validity(mp)
        assert isinstance(findings, list)

    def test_nonexistent_marketplace_no_crash(self, tmp_path: Path) -> None:
        """Non-existent marketplace root returns empty list."""
        mp = tmp_path / 'does-not-exist'
        findings = analyze_metadata_field_validity(mp)
        assert findings == []
