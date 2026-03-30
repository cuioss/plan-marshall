#!/usr/bin/env python3
"""Deep tests for maintain.py subcommands: analyze, check-duplication, update, readme.

Tests exercise fixture-based scenarios beyond the basic help/missing-args tests
in test_maintain.py. Each subcommand section covers happy paths, edge cases,
and error conditions using the existing fixtures directory.
"""

import json
import tempfile
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-maintain', 'maintain.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# =============================================================================
# Analyze subcommand — fixture-based
# =============================================================================


def test_analyze_perfect_agent():
    """Analyze a well-structured agent gives high quality score."""
    fixture = FIXTURES_DIR / 'components' / 'perfect-agent.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    assert data['quality_score'] >= 80, f'Perfect agent should score high, got {data["quality_score"]}'
    assert data['component_type'] == 'unknown'  # path has no /agents/ segment
    assert data['stats']['total_lines'] > 0
    assert data['stats']['sections'] > 0


def test_analyze_no_frontmatter():
    """Analyze component without frontmatter reports missing-frontmatter issue."""
    fixture = FIXTURES_DIR / 'components' / 'no-frontmatter.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    assert any(i['type'] == 'missing-frontmatter' for i in data['issues'])
    assert data['quality_score'] < 80


def test_analyze_tool_compliance_violation():
    """Analyze agent with Task tool reports compliance issue."""
    fixture = FIXTURES_DIR / 'components' / 'tool-compliance-violation.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    assert any(i['type'] == 'agent-task-tool-prohibited' for i in data['issues'])
    assert data['quality_score'] < 100


def test_analyze_missing_sections_agent():
    """Analyze agent with missing sections reports missing sections."""
    fixture = FIXTURES_DIR / 'components' / 'missing-sections-agent.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    # Should have sections_found but also missing sections in suggestions
    assert 'suggestions' in data
    assert data['stats']['sections'] >= 1


def test_analyze_nonexistent_file_returns_error():
    """Analyze on nonexistent path returns error dict."""
    result = run_script(SCRIPT_PATH, 'analyze', '--component', '/nonexistent/component.md')
    data = parse_toon(result.stdout)
    assert 'error' in data
    assert result.returncode != 0


def test_analyze_empty_component():
    """Analyze empty component file."""
    fixture = FIXTURES_DIR / 'components' / 'empty-component.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    assert 'quality_score' in data


def test_analyze_returns_stats():
    """Analyze output includes stats with expected keys."""
    fixture = FIXTURES_DIR / 'components' / 'perfect-agent.md'
    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(fixture))
    data = parse_toon(result.stdout)
    stats = data['stats']
    assert 'total_lines' in stats
    assert 'frontmatter_lines' in stats
    assert 'body_lines' in stats
    assert 'sections' in stats
    assert stats['frontmatter_lines'] > 0


# =============================================================================
# Check-duplication subcommand — fixture-based
# =============================================================================


def test_checkdup_high_duplicate():
    """Check-duplication analyzes overlap with existing references without error."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-high-duplicate.md'
    result = run_script(
        SCRIPT_PATH, 'check-duplication',
        '--skill-path', str(skill_path),
        '--content-file', str(content_file),
    )
    data = parse_toon(result.stdout)
    assert 'error' not in data
    assert result.returncode == 0
    # Result has all expected keys
    assert 'duplication_detected' in data
    assert 'duplication_percentage' in data
    assert 'duplicate_files' in data
    assert 'recommendation' in data
    # The percentage should be a number (may or may not exceed threshold)
    assert isinstance(data['duplication_percentage'], (int, float))


def test_checkdup_exact_duplicate_detected():
    """Check-duplication detects exact duplicate content via inline fixtures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / 'test-skill'
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir(parents=True)
        # Create an existing reference
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
        # Create new content that is nearly identical
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
        result = run_script(
            SCRIPT_PATH, 'check-duplication',
            '--skill-path', str(skill_dir),
            '--content-file', str(new_file),
        )
        data = parse_toon(result.stdout)
        assert 'error' not in data
        assert data['duplication_detected'] is True
        assert data['duplication_percentage'] > 60
        assert len(data['duplicate_files']) > 0


def test_checkdup_unique_content():
    """Check-duplication reports no duplication for unique content."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-unique-content.md'
    result = run_script(
        SCRIPT_PATH, 'check-duplication',
        '--skill-path', str(skill_path),
        '--content-file', str(content_file),
    )
    data = parse_toon(result.stdout)
    assert 'error' not in data
    assert data['recommendation'] == 'proceed'


def test_checkdup_empty_content():
    """Check-duplication handles empty/minimal content file."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-empty.md'
    result = run_script(
        SCRIPT_PATH, 'check-duplication',
        '--skill-path', str(skill_path),
        '--content-file', str(content_file),
    )
    data = parse_toon(result.stdout)
    assert 'error' not in data
    assert data['duplication_detected'] is False
    assert data['recommendation'] == 'proceed'


def test_checkdup_no_references_dir():
    """Check-duplication handles skill without references directory."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-no-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-unique-content.md'
    result = run_script(
        SCRIPT_PATH, 'check-duplication',
        '--skill-path', str(skill_path),
        '--content-file', str(content_file),
    )
    data = parse_toon(result.stdout)
    assert 'error' not in data
    assert data['duplication_detected'] is False
    assert data['recommendation'] == 'proceed'


def test_checkdup_nonexistent_content_file():
    """Check-duplication returns error for missing content file."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    result = run_script(
        SCRIPT_PATH, 'check-duplication',
        '--skill-path', str(skill_path),
        '--content-file', '/nonexistent/file.md',
    )
    data = parse_toon(result.stdout)
    assert 'error' in data


def test_checkdup_result_has_expected_keys():
    """Check-duplication result includes all expected top-level keys."""
    skill_path = FIXTURES_DIR / 'knowledge' / 'skill-with-references'
    content_file = FIXTURES_DIR / 'knowledge' / 'new-unique-content.md'
    result = run_script(
        SCRIPT_PATH, 'check-duplication',
        '--skill-path', str(skill_path),
        '--content-file', str(content_file),
    )
    data = parse_toon(result.stdout)
    for key in ['skill_path', 'new_content_file', 'duplication_detected',
                'duplication_percentage', 'duplicate_files', 'recommendation']:
        assert key in data, f'Missing key: {key}'


# =============================================================================
# Update subcommand — temp file based
# =============================================================================


def test_update_frontmatter_field():
    """Update adds a new frontmatter field."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Original\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': [{'type': 'frontmatter', 'field': 'version', 'value': '2.0'}]})
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
        assert data['success'] is True
        assert data['updates_applied'] == 1
        # Verify the file was actually modified
        content = Path(f.name).read_text()
        assert 'version: 2.0' in content
        # Clean up
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
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
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
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
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
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
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
        updates = json.dumps({'updates': [
            {'type': 'frontmatter', 'field': 'version', 'value': '1.0'},
            {'type': 'append', 'text': '## Footer\n\nEnd.'},
        ]})
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
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
    result = run_script(SCRIPT_PATH, 'update', '--component', '/nonexistent/file.md', '--updates', updates)
    data = parse_toon(result.stdout)
    assert data['success'] is False
    assert 'error' in data


def test_update_invalid_json():
    """Update with malformed JSON returns error."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n')
        f.flush()
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', 'not-json')
        data = parse_toon(result.stdout)
        assert 'error' in data
        assert result.returncode != 0
        Path(f.name).unlink()


def test_update_empty_updates_list():
    """Update with empty updates list succeeds with zero applied."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\n---\n\n# Test\n')
        f.flush()
        updates = json.dumps({'updates': []})
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
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
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
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
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = parse_toon(result.stdout)
        assert data['success'] is True
        content = Path(f.name).read_text()
        assert content.startswith('---')
        assert 'name: new-name' in content
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


# =============================================================================
# Readme subcommand — fixture-based
# =============================================================================


def test_readme_complete_bundle():
    """Readme for complete bundle discovers all component types."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    data = parse_toon(result.stdout)
    assert data['readme_generated'] is True
    assert data['bundle_name'] == 'test-bundle'
    assert data['components']['commands'] >= 1
    assert data['components']['agents'] >= 1
    assert data['components']['skills'] >= 1
    # Multiline readme_content checked via stdout (TOON multiline limitation)
    assert '## Commands' in result.stdout
    assert '## Agents' in result.stdout
    assert '## Skills' in result.stdout


def test_readme_commands_only_bundle():
    """Readme for bundle with only commands omits agents/skills sections."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-commands-only'
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    data = parse_toon(result.stdout)
    assert data['readme_generated'] is True
    assert data['components']['commands'] >= 1
    assert data['components']['agents'] == 0
    assert data['components']['skills'] == 0
    assert '## Commands' in result.stdout
    assert '## Agents' not in result.stdout


def test_readme_empty_bundle():
    """Readme for empty bundle succeeds with zero components."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-empty'
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    data = parse_toon(result.stdout)
    assert data['readme_generated'] is True
    assert data['components']['commands'] == 0
    assert data['components']['agents'] == 0
    assert data['components']['skills'] == 0


def test_readme_nonexistent_bundle():
    """Readme for nonexistent path returns error."""
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', '/nonexistent/bundle')
    data = parse_toon(result.stdout)
    assert 'error' in data
    assert result.returncode != 0


def test_readme_directory_without_plugin_json():
    """Readme for directory without plugin.json returns error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', tmpdir)
        data = parse_toon(result.stdout)
        assert 'error' in data
        assert 'plugin.json' in data['error']


def test_readme_includes_installation_section():
    """Readme output includes Installation section."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    assert '## Installation' in result.stdout


def test_readme_result_has_component_lists():
    """Readme result includes lists of commands, agents, skills."""
    bundle_path = FIXTURES_DIR / 'readmes' / 'bundle-complete'
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    data = parse_toon(result.stdout)
    assert 'commands' in data
    assert 'agents' in data
    assert 'skills' in data
    assert isinstance(data['commands'], list)
    # Each item should have name and description
    if data['commands']:
        cmd = data['commands'][0]
        assert 'name' in cmd
        assert 'description' in cmd
