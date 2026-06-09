# ruff: noqa: I001, E402
"""Tests for the ``declared-component-vs-disk`` rule analyzer.

The analyzer scans every bundle's ``.claude-plugin/plugin.json`` under the
marketplace bundles root and, for each component declared under ``agents`` /
``commands`` / ``skills``, asserts that the corresponding file exists on disk.
A declared entry whose target file is missing produces a finding. This is the
forward-direction half of the bidirectional plugin.json manifest-integrity
check (the reverse — on-disk-but-undeclared — lives in
``_analyze_plugin_json.py``).

Entry shapes:
  * skills: ``./skills/{skill}`` → anchor ``{bundle}/skills/{skill}/SKILL.md``
  * agents: ``./agents/{agent}.md`` → anchor ``{bundle}/agents/{agent}.md``
  * commands: ``./commands/{command}.md`` → anchor the markdown file directly

Test layers:
  * Declared component whose file exists → no finding (positive case)
  * Declared component whose file is missing → one finding (negative case)
  * Boundary: ``./`` prefix optional, skill-dir vs file anchoring, malformed
    manifest skipped, empty root returns no findings
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_advd = _load_module('_analyze_declared_vs_disk', '_analyze_declared_vs_disk.py')

analyze_declared_vs_disk = _advd.analyze_declared_vs_disk
RULE_ID = _advd.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace bundles tree.
# ---------------------------------------------------------------------------


def _write_plugin_json(bundle_dir: Path, manifest: dict) -> Path:
    """Write ``{bundle}/.claude-plugin/plugin.json`` and return its path."""
    import json

    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_json = plugin_dir / 'plugin.json'
    plugin_json.write_text(json.dumps(manifest), encoding='utf-8')
    return plugin_json


def _make_skill(bundle_dir: Path, skill: str) -> None:
    """Create ``{bundle}/skills/{skill}/SKILL.md`` on disk."""
    skill_dir = bundle_dir / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text('# stub\n', encoding='utf-8')


def _make_agent(bundle_dir: Path, agent: str) -> None:
    """Create ``{bundle}/agents/{agent}.md`` on disk."""
    agents_dir = bundle_dir / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f'{agent}.md').write_text('# stub\n', encoding='utf-8')


def _make_command(bundle_dir: Path, command: str) -> None:
    """Create ``{bundle}/commands/{command}.md`` on disk."""
    commands_dir = bundle_dir / 'commands'
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / f'{command}.md').write_text('# stub\n', encoding='utf-8')


# ===========================================================================
# Positive cases — declared component whose file exists → no finding.
# ===========================================================================


class TestDeclaredComponentResolves:
    """A declared entry whose anchor file exists produces no findings."""

    def test_declared_skill_with_skill_md_present(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'my-skill')
        _write_plugin_json(bundle, {'skills': ['./skills/my-skill']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []

    def test_declared_agent_and_command_present(self, tmp_path: Path) -> None:
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

        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []

    def test_entry_without_leading_dot_slash_resolves(self, tmp_path: Path) -> None:
        """The leading ``./`` is optional — a bare relative path resolves too."""
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'my-skill')
        _write_plugin_json(bundle, {'skills': ['skills/my-skill']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        """An empty bundles root (no plugin.json files) yields no findings."""
        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []


# ===========================================================================
# Negative cases — declared component whose file is missing → one finding.
# ===========================================================================


class TestDeclaredComponentMissing:
    """A declared entry whose anchor file is absent produces one finding."""

    def test_declared_skill_missing_skill_md(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        # No skill dir / SKILL.md created — only the manifest declares it.
        plugin_json = _write_plugin_json(bundle, {'skills': ['./skills/ghost-skill']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'error'
        assert finding['fixable'] is False
        assert finding['file'] == str(plugin_json)
        assert finding['line'] == 1
        details = finding['details']
        assert details['bundle'] == 'my-bundle'
        assert details['component_kind'] == 'skill'
        assert details['declared_entry'] == './skills/ghost-skill'
        assert details['reason'] == 'declared_file_missing'
        assert details['expected_path'].endswith('skills/ghost-skill/SKILL.md')

    def test_declared_agent_missing_file(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        plugin_json = _write_plugin_json(bundle, {'agents': ['./agents/ghost-agent.md']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['details']['component_kind'] == 'agent'
        assert finding['file'] == str(plugin_json)
        assert finding['details']['expected_path'].endswith('agents/ghost-agent.md')

    def test_declared_command_missing_file(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _write_plugin_json(bundle, {'commands': ['./commands/ghost-command.md']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['component_kind'] == 'command'

    def test_skill_dir_present_but_skill_md_missing_is_flagged(self, tmp_path: Path) -> None:
        """A skill entry resolves to the directory's SKILL.md, not the dir itself.

        A ``skills/{skill}/`` directory with no ``SKILL.md`` is still an
        unresolved declaration — the anchor is the file, not the folder.
        """
        bundle = tmp_path / 'my-bundle'
        (bundle / 'skills' / 'hollow-skill').mkdir(parents=True)
        _write_plugin_json(bundle, {'skills': ['./skills/hollow-skill']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details']['component_kind'] == 'skill'

    def test_mixed_present_and_missing_flags_only_missing(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _make_skill(bundle, 'present-skill')
        _make_agent(bundle, 'present-agent')
        _write_plugin_json(
            bundle,
            {
                'skills': ['./skills/present-skill', './skills/missing-skill'],
                'agents': ['./agents/present-agent.md', './agents/missing-agent.md'],
            },
        )

        findings = analyze_declared_vs_disk(tmp_path)

        assert len(findings) == 2
        missing = {f['details']['declared_entry'] for f in findings}
        assert missing == {'./skills/missing-skill', './agents/missing-agent.md'}


# ===========================================================================
# Boundary cases — malformed input, non-string entries, multi-bundle.
# ===========================================================================


class TestBoundaryConditions:
    """Malformed manifests and non-component entries are handled gracefully."""

    def test_malformed_json_manifest_is_skipped(self, tmp_path: Path) -> None:
        """An unparseable plugin.json is not this rule's failure mode."""
        bundle = tmp_path / 'my-bundle'
        plugin_dir = bundle / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'plugin.json').write_text('{ this is not valid json', encoding='utf-8')

        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []

    def test_non_string_and_blank_entries_ignored(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _write_plugin_json(
            bundle,
            {'skills': [123, '', '   ', None]},
        )

        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []

    def test_non_list_component_value_ignored(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _write_plugin_json(bundle, {'skills': 'not-a-list'})

        findings = analyze_declared_vs_disk(tmp_path)

        assert findings == []

    def test_findings_span_multiple_bundles(self, tmp_path: Path) -> None:
        bundle_a = tmp_path / 'bundle-a'
        bundle_b = tmp_path / 'bundle-b'
        _write_plugin_json(bundle_a, {'skills': ['./skills/ghost-a']})
        _write_plugin_json(bundle_b, {'agents': ['./agents/ghost-b.md']})

        findings = analyze_declared_vs_disk(tmp_path)

        assert len(findings) == 2
        bundles = {f['details']['bundle'] for f in findings}
        assert bundles == {'bundle-a', 'bundle-b'}
