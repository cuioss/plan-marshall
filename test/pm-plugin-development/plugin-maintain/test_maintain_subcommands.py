#!/usr/bin/env python3
"""Deep tests for maintain.py subcommands: analyze, check-duplication, update, readme.

Tests exercise fixture-based scenarios beyond the basic help/missing-args tests
in test_maintain.py. Each subcommand section covers happy paths, edge cases,
and error conditions using the existing fixtures directory.
"""

import json
import tempfile
from argparse import Namespace
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-maintain', 'maintain.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-maintain' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_cmd_analyze_mod = _load_module('_cmd_analyze', '_cmd_analyze.py')
_cmd_check_duplication_mod = _load_module('_cmd_check_duplication', '_cmd_check_duplication.py')
_cmd_readme_mod = _load_module('_cmd_readme', '_cmd_readme.py')
_cmd_update_mod = _load_module('_cmd_update', '_cmd_update.py')

cmd_analyze = _cmd_analyze_mod.cmd_analyze
cmd_check_duplication = _cmd_check_duplication_mod.cmd_check_duplication
cmd_readme = _cmd_readme_mod.cmd_readme
cmd_update = _cmd_update_mod.cmd_update

# =============================================================================
# CLI plumbing tests (Tier 3 - subprocess)
# =============================================================================


def test_analyze_perfect_agent_cli():
    """Analyze a well-structured agent via CLI gives high quality score."""
    fixture = FIXTURES_DIR / 'components' / 'perfect-agent.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    assert data['quality_score'] >= 80, f'Perfect agent should score high, got {data["quality_score"]}'


def test_readme_complete_bundle_cli():
    """Readme for complete bundle via CLI discovers all component types."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    data = parse_toon(result.stdout)
    assert data['readme_generated'] is True


# =============================================================================
# Analyze subcommand -- fixture-based (Tier 2 - direct import)
# =============================================================================


def test_analyze_perfect_agent():
    """Analyze a well-structured agent gives high quality score."""
    fixture = FIXTURES_DIR / 'components' / 'perfect-agent.md'
    args = Namespace(component=str(fixture))
    data = cmd_analyze(args)
    assert data['quality_score'] >= 80, f'Perfect agent should score high, got {data["quality_score"]}'
    assert data['component_type'] == 'unknown'  # path has no /agents/ segment
    assert data['stats']['total_lines'] > 0
    assert data['stats']['sections'] > 0


def test_analyze_no_frontmatter():
    """Analyze component without frontmatter reports missing-frontmatter issue."""
    fixture = FIXTURES_DIR / 'components' / 'no-frontmatter.md'
    args = Namespace(component=str(fixture))
    data = cmd_analyze(args)
    assert any(i['type'] == 'missing-frontmatter' for i in data['issues'])
    assert data['quality_score'] < 80


def test_analyze_tool_compliance_violation():
    """Analyze agent with Task tool reports compliance issue."""
    fixture = FIXTURES_DIR / 'components' / 'tool-compliance-violation.md'
    args = Namespace(component=str(fixture))
    data = cmd_analyze(args)
    assert any(i['type'] == 'agent-task-tool-prohibited' for i in data['issues'])
    assert data['quality_score'] < 100


def test_analyze_missing_sections_agent():
    """Analyze agent with missing sections reports missing sections."""
    fixture = FIXTURES_DIR / 'components' / 'missing-sections-agent.md'
    args = Namespace(component=str(fixture))
    data = cmd_analyze(args)
    assert 'suggestions' in data
    assert data['stats']['sections'] >= 1


def test_analyze_nonexistent_file_returns_error():
    """Analyze on nonexistent path returns error dict."""
    args = Namespace(component='/nonexistent/component.md')
    data = cmd_analyze(args)
    assert 'error' in data
    assert data.get('status') == 'error'


def test_analyze_empty_component():
    """Analyze empty component file."""
    fixture = FIXTURES_DIR / 'components' / 'empty-component.md'
    args = Namespace(component=str(fixture))
    data = cmd_analyze(args)
    assert 'quality_score' in data


def test_analyze_returns_stats():
    """Analyze output includes stats with expected keys."""
    fixture = FIXTURES_DIR / 'components' / 'perfect-agent.md'
    args = Namespace(component=str(fixture))
    data = cmd_analyze(args)
    stats = data['stats']
    assert 'total_lines' in stats
    assert 'frontmatter_lines' in stats
    assert 'body_lines' in stats
    assert 'sections' in stats
    assert stats['frontmatter_lines'] > 0


# =============================================================================
# Check-duplication subcommand -- fixture-based (Tier 2 - direct import)
# =============================================================================


def test_checkdup_high_duplicate():
    """Check-duplication analyzes overlap with existing references without error."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-high-duplicate.md'
    args = Namespace(skill_path=str(skill_path), content_file=str(content_file))
    data = cmd_check_duplication(args)
    assert 'error' not in data
    assert 'duplication_detected' in data
    assert 'duplication_percentage' in data
    assert 'duplicate_files' in data
    assert 'recommendation' in data
    assert isinstance(data['duplication_percentage'], (int, float))


def test_checkdup_exact_duplicate_detected():
    """Check-duplication detects exact duplicate content via inline fixtures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / 'test-skill'
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir(parents=True)
        existing = refs_dir / 'existing.md'
        existing.write_text(
            '# Guide\n\n## Section One\n\n'
            'This is a substantial paragraph with enough content to exceed the '
            'hundred character threshold for duplication detection in the check '
            'duplication script logic.\n\n'
            '## Section Two\n\n'
            'Another substantial paragraph that provides enough textual mass for '
            'the similarity algorithm to detect meaningful overlap between files.\n'
        )
        new_file = Path(tmpdir) / 'new-content.md'
        new_file.write_text(
            '# Guide\n\n## Section One\n\n'
            'This is a substantial paragraph with enough content to exceed the '
            'hundred character threshold for duplication detection in the check '
            'duplication script logic.\n\n'
            '## Section Two\n\n'
            'Another substantial paragraph that provides enough textual mass for '
            'the similarity algorithm to detect meaningful overlap between files.\n'
        )
        args = Namespace(skill_path=str(skill_dir), content_file=str(new_file))
        data = cmd_check_duplication(args)
        assert 'error' not in data
        assert data['duplication_detected'] is True
        assert data['duplication_percentage'] > 60
        assert len(data['duplicate_files']) > 0


def test_checkdup_unique_content():
    """Check-duplication reports no duplication for unique content."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-unique-content.md'
    args = Namespace(skill_path=str(skill_path), content_file=str(content_file))
    data = cmd_check_duplication(args)
    assert 'error' not in data
    assert data['recommendation'] == 'proceed'


def test_checkdup_empty_content():
    """Check-duplication handles empty/minimal content file."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-empty.md'
    args = Namespace(skill_path=str(skill_path), content_file=str(content_file))
    data = cmd_check_duplication(args)
    assert 'error' not in data
    assert data['duplication_detected'] is False
    assert data['recommendation'] == 'proceed'


def test_checkdup_no_references_dir():
    """Check-duplication handles skill without references directory."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-no-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-unique-content.md'
    args = Namespace(skill_path=str(skill_path), content_file=str(content_file))
    data = cmd_check_duplication(args)
    assert 'error' not in data
    assert data['duplication_detected'] is False
    assert data['recommendation'] == 'proceed'


def test_checkdup_nonexistent_content_file():
    """Check-duplication returns error for missing content file."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    args = Namespace(skill_path=str(skill_path), content_file='/nonexistent/file.md')
    data = cmd_check_duplication(args)
    assert 'error' in data


def test_checkdup_result_has_expected_keys():
    """Check-duplication result includes all expected top-level keys."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-unique-content.md'
    args = Namespace(skill_path=str(skill_path), content_file=str(content_file))
    data = cmd_check_duplication(args)
    for key in [
        'skill_path',
        'new_content_file',
        'duplication_detected',
        'duplication_percentage',
        'duplicate_files',
        'recommendation',
    ]:
        assert key in data, f'Missing key: {key}'


# =============================================================================
# Update subcommand -- temp file based (Tier 2 - direct import)
# =============================================================================


def test_update_frontmatter_field():
    """Update adds a new frontmatter field."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Original\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'frontmatter', 'field': 'version', 'value': '2.0'}]})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        assert data['updates_applied'] == 1
        content = Path(f.name).read_text()
        assert 'version: 2.0' in content
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


def test_update_existing_frontmatter_field():
    """Update modifies an existing frontmatter field."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Original\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'frontmatter', 'field': 'description', 'value': 'Updated'}]})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        content = Path(f.name).read_text()
        assert 'description: Updated' in content
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


def test_update_replace_text():
    """Update replaces text in content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n\nOld text here.\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'replace', 'old': 'Old text here.', 'new': 'New text here.'}]})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        assert data['updates_applied'] == 1
        content = Path(f.name).read_text()
        assert 'New text here.' in content
        assert 'Old text here.' not in content
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


def test_update_append_text():
    """Update appends text to end of content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'append', 'text': '## New Section\n\nNew content.'}]})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        content = Path(f.name).read_text()
        assert '## New Section' in content
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


def test_update_multiple_updates():
    """Update applies multiple updates in sequence."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Old\n---\n\n# Test\n\nSome text.\n')
        f.flush()
        updates = json.dumps(
            {
                'updates': [
                    {'type': 'frontmatter', 'field': 'version', 'value': '1.0'},
                    {'type': 'append', 'text': '## Footer\n\nEnd.'},
                ]
            }
        )
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        assert data['updates_applied'] == 2
        assert len(data['changes']) == 2
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


def test_update_nonexistent_file():
    """Update on nonexistent file returns error."""
    updates = json.dumps({'updates': [{'type': 'frontmatter', 'field': 'v', 'value': '1'}]})
    args = Namespace(component='/nonexistent/file.md', updates=updates)
    data = cmd_update(args)
    assert data['success'] is False
    assert 'error' in data


def test_update_invalid_json():
    """Update with malformed JSON returns error."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n')
        f.flush()
        args = Namespace(component=f.name, updates='not-json')
        data = cmd_update(args)
        assert 'error' in data
        assert data.get('status') == 'error'
        Path(f.name).unlink()


def test_update_empty_updates_list():
    """Update with empty updates list succeeds with zero applied."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': []})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        assert data['updates_applied'] == 0
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


def test_update_creates_backup():
    """Update creates a .maintain-backup file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'frontmatter', 'field': 'v', 'value': '1'}]})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        backup = Path(f.name + '.maintain-backup')
        assert backup.exists(), 'Backup file should exist'
        backup.unlink()
        Path(f.name).unlink()


def test_update_frontmatter_on_file_without_frontmatter():
    """Update adds frontmatter to file that has none."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('# No Frontmatter\n\nJust content.\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'frontmatter', 'field': 'name', 'value': 'new-name'}]})
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data['success'] is True
        content = Path(f.name).read_text()
        assert content.startswith('---')
        assert 'name: new-name' in content
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


# =============================================================================
# Readme subcommand -- fixture-based (Tier 2 - direct import)
# =============================================================================


def test_readme_complete_bundle():
    """Readme for complete bundle discovers all component types."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    args = Namespace(bundle_path=str(bundle_path))
    data = cmd_readme(args)
    assert data['readme_generated'] is True
    assert data['bundle_name'] == 'test-bundle'
    assert data['components']['commands'] >= 1
    assert data['components']['agents'] >= 1
    assert data['components']['skills'] >= 1
    readme = data.get('readme_content', '')
    assert '## Commands' in readme
    assert '## Agents' in readme
    assert '## Skills' in readme


def test_readme_commands_only_bundle():
    """Readme for bundle with only commands omits agents/skills sections."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-commands-only'
    args = Namespace(bundle_path=str(bundle_path))
    data = cmd_readme(args)
    assert data['readme_generated'] is True
    assert data['components']['commands'] >= 1
    assert data['components']['agents'] == 0
    assert data['components']['skills'] == 0
    readme = data.get('readme_content', '')
    assert '## Commands' in readme
    assert '## Agents' not in readme


def test_readme_empty_bundle():
    """Readme for empty bundle succeeds with zero components."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-empty'
    args = Namespace(bundle_path=str(bundle_path))
    data = cmd_readme(args)
    assert data['readme_generated'] is True
    assert data['components']['commands'] == 0
    assert data['components']['agents'] == 0
    assert data['components']['skills'] == 0


def test_readme_nonexistent_bundle():
    """Readme for nonexistent path returns error."""
    args = Namespace(bundle_path='/nonexistent/bundle')
    data = cmd_readme(args)
    assert 'error' in data
    assert data.get('status') == 'error'


def test_readme_directory_without_plugin_json():
    """Readme for directory without plugin.json returns error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        args = Namespace(bundle_path=tmpdir)
        data = cmd_readme(args)
        assert data.get('status') == 'error'
        assert 'plugin.json' in data.get('message', '') or 'plugin_json' in data.get('error', '')


def test_readme_includes_installation_section():
    """Readme output includes Installation section."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    args = Namespace(bundle_path=str(bundle_path))
    data = cmd_readme(args)
    readme = data.get('readme_content', '')
    assert '## Installation' in readme


def test_readme_result_has_component_lists():
    """Readme result includes lists of commands, agents, skills."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    args = Namespace(bundle_path=str(bundle_path))
    data = cmd_readme(args)
    assert 'commands' in data
    assert 'agents' in data
    assert 'skills' in data
    assert isinstance(data['commands'], list)
    if data['commands']:
        cmd = data['commands'][0]
        assert 'name' in cmd
        assert 'description' in cmd


# =============================================================================
# Main
# =============================================================================
