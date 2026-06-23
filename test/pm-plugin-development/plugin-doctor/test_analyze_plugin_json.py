# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``plugin-json-orphan-component`` rule analyzer.

This module houses the reverse-direction half of the plugin.json
manifest-integrity check: every on-disk component a bundle ships under
``skills/*/SKILL.md`` / ``agents/*.md`` / ``commands/*.md`` must be declared in
its bundle's ``plugin.json`` — UNLESS legitimately unregistered per the
marketplace registration convention.

Registration convention (the exemption):
  * user-invocable skills (``user-invocable: true``) MUST register — an
    undeclared one is a real orphan.
  * context-loaded / script-only / extension-implementor skills
    (``user-invocable: false`` or no frontmatter) are legitimately
    unregistered — exempt.
  * agents and commands always register — any undeclared file is an orphan.

The rule is advisory (``severity: warning``, ``fixable: false``).

The module also re-exports the forward-direction ``analyze_declared_vs_disk``
analyzer; this test pins that re-export so the orchestrator's single import
site stays valid.

Test layers:
  * On-disk component declared in plugin.json → no finding (positive)
  * Undeclared user-invocable skill / agent / command → one finding (negative)
  * Boundary: user-invocable: false skill exempt, malformed manifest skipped,
    re-export wiring intact
"""

import json
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_apj = _load_module('_analyze_plugin_json', '_analyze_plugin_json.py')

analyze_plugin_json_orphans = _apj.analyze_plugin_json_orphans
RULE_ID = _apj.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace bundles tree.
# ---------------------------------------------------------------------------


def _write_plugin_json(bundle_dir: Path, manifest: dict) -> Path:
    """Write ``{bundle}/.claude-plugin/plugin.json`` and return its path."""
    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_json = plugin_dir / 'plugin.json'
    plugin_json.write_text(json.dumps(manifest), encoding='utf-8')
    return plugin_json


def _make_skill(bundle_dir: Path, skill: str, *, user_invocable: bool | None) -> Path:
    """Create ``{bundle}/skills/{skill}/SKILL.md``.

    ``user_invocable`` controls the frontmatter: ``True`` / ``False`` write a
    ``user-invocable:`` scalar; ``None`` writes a SKILL.md with no frontmatter
    at all (so the orphan rule treats it as not user-invocable → exempt).
    """
    skill_dir = bundle_dir / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    if user_invocable is None:
        md.write_text('# No frontmatter\n', encoding='utf-8')
    else:
        value = 'true' if user_invocable else 'false'
        md.write_text(
            f'---\nname: {skill}\nuser-invocable: {value}\n---\n\n# {skill}\n',
            encoding='utf-8',
        )
    return md


def _make_agent(bundle_dir: Path, agent: str) -> Path:
    agents_dir = bundle_dir / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    md = agents_dir / f'{agent}.md'
    md.write_text('# stub\n', encoding='utf-8')
    return md


def _make_command(bundle_dir: Path, command: str) -> Path:
    commands_dir = bundle_dir / 'commands'
    commands_dir.mkdir(parents=True, exist_ok=True)
    md = commands_dir / f'{command}.md'
    md.write_text('# stub\n', encoding='utf-8')
    return md


# ===========================================================================
# Positive cases — declared on-disk component → no finding.
# ===========================================================================


class TestComponentDeclared:
    """An on-disk component declared in plugin.json produces no findings."""

    def test_declared_user_invocable_skill_silent(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'my-skill', user_invocable=True)
        _write_plugin_json(bundle, {'skills': ['./skills/my-skill']})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []

    def test_declared_agent_and_command_silent(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_agent(bundle, 'my-agent')
        _make_command(bundle, 'my-command')
        _write_plugin_json(
            bundle,
            {
                'agents': ['./agents/my-agent.md'],
                'commands': ['./commands/my-command.md'],
            },
        )

        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []


# ===========================================================================
# Negative cases — undeclared on-disk component → one finding.
# ===========================================================================


class TestOrphanComponent:
    """An undeclared on-disk component produces one warning finding."""

    def test_undeclared_user_invocable_skill_flagged(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        skill_md = _make_skill(bundle, 'orphan-skill', user_invocable=True)
        # plugin.json declares NOTHING — the skill is an orphan.
        _write_plugin_json(bundle, {})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert finding['file'] == str(skill_md)
        details = finding['details']
        assert details['bundle'] == 'my-bundle'
        assert details['component_kind'] == 'skill'
        assert details['disk_entry'] == 'skills/orphan-skill'
        assert details['reason'] == 'undeclared_on_disk_component'

    def test_undeclared_agent_flagged(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        agent_md = _make_agent(bundle, 'orphan-agent')
        _write_plugin_json(bundle, {})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['details']['component_kind'] == 'agent'
        assert finding['details']['disk_entry'] == 'agents/orphan-agent.md'
        assert finding['file'] == str(agent_md)

    def test_undeclared_command_flagged(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_command(bundle, 'orphan-command')
        _write_plugin_json(bundle, {})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['component_kind'] == 'command'

    def test_only_undeclared_components_flagged(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'declared-skill', user_invocable=True)
        _make_skill(bundle, 'orphan-skill', user_invocable=True)
        _write_plugin_json(bundle, {'skills': ['./skills/declared-skill']})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['disk_entry'] == 'skills/orphan-skill'


# ===========================================================================
# Boundary cases — registration-convention exemption and malformed input.
# ===========================================================================


class TestRegistrationExemption:
    """Non-user-invocable skills are exempt from the orphan rule."""

    def test_user_invocable_false_skill_exempt(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'script-only-skill', user_invocable=False)
        _write_plugin_json(bundle, {})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []

    def test_skill_without_frontmatter_exempt(self, tmp_path: Path) -> None:
        """A SKILL.md with no frontmatter is treated as not-user-invocable → exempt."""
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'context-skill', user_invocable=None)
        _write_plugin_json(bundle, {})

        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []

    def test_malformed_manifest_skipped(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'orphan-skill', user_invocable=True)
        plugin_dir = bundle / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'plugin.json').write_text('{ broken', encoding='utf-8')

        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []

    def test_directory_without_plugin_json_not_a_bundle(self, tmp_path: Path) -> None:
        """A directory lacking ``.claude-plugin/plugin.json`` is not scanned."""
        stray = tmp_path / 'not-a-bundle' / 'skills' / 'orphan'
        stray.mkdir(parents=True)
        (stray / 'SKILL.md').write_text(
            '---\nname: orphan\nuser-invocable: true\n---\n', encoding='utf-8'
        )

        findings = analyze_plugin_json_orphans(tmp_path)

        assert findings == []


# ===========================================================================
# Re-export wiring — forward-direction analyzer is importable from here.
# ===========================================================================


class TestForwardReexport:
    """The module re-exports the forward-direction declared-vs-disk analyzer."""

    def test_analyze_declared_vs_disk_reexported(self) -> None:
        assert hasattr(_apj, 'analyze_declared_vs_disk')
        assert callable(_apj.analyze_declared_vs_disk)

    def test_reexport_in_dunder_all(self) -> None:
        assert 'analyze_declared_vs_disk' in _apj.__all__
        assert 'analyze_plugin_json_orphans' in _apj.__all__
