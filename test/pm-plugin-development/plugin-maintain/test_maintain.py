#!/usr/bin/env python3
"""Tests for maintain.py - consolidated plugin maintenance tools.

Tests plugin maintenance capabilities including:
- update: Apply updates to a component
- check-duplication: Check for duplicate knowledge
- analyze: Analyze component for quality
- readme: Generate README for a bundle
"""

import tempfile
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-maintain', 'maintain.py')


# =============================================================================
# Main help tests
# =============================================================================

def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f"Script not found: {SCRIPT_PATH}"


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'update' in combined, "update subcommand in help"
    assert 'check-duplication' in combined, "check-duplication subcommand in help"
    assert 'analyze' in combined, "analyze subcommand in help"
    assert 'readme' in combined, "readme subcommand in help"


# =============================================================================
# Update Subcommand Tests
# =============================================================================

def test_update_help():
    """Test update --help is available."""
    result = run_script(SCRIPT_PATH, 'update', '--help')
    assert 'component' in result.stdout or 'component' in result.stderr, \
        "Help should mention component option"


def test_update_missing_component():
    """Test update requires component."""
    result = run_script(SCRIPT_PATH, 'update')
    assert result.returncode != 0, "Should error without component"


def test_update_with_updates_arg():
    """Test update with --updates argument."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Original\n---\n\n# Test\n')
        f.flush()

        updates = '{"updates": [{"type": "frontmatter", "field": "version", "value": "1.0"}]}'
        result = run_script(SCRIPT_PATH, 'update', '--component', f.name, '--updates', updates)
        data = result.json()
        assert data is not None, "Should return valid JSON"

        # Clean up backup if created
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


# =============================================================================
# Check-Duplication Subcommand Tests
# =============================================================================

def test_checkdup_help():
    """Test check-duplication --help is available."""
    result = run_script(SCRIPT_PATH, 'check-duplication', '--help')
    combined = result.stdout + result.stderr
    assert 'skill-path' in combined, "Help should mention skill-path"
    assert 'content-file' in combined, "Help should mention content-file"


def test_checkdup_missing_arguments():
    """Test check-duplication requires arguments."""
    result = run_script(SCRIPT_PATH, 'check-duplication')
    assert result.returncode != 0, "Should error without arguments"


def test_checkdup_nonexistent_skill():
    """Test check-duplication handles nonexistent skill path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('# Some content\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'check-duplication',
                          '--skill-path', '/nonexistent/skill',
                          '--content-file', f.name)
        data = result.json()
        assert data is not None, "Should return valid JSON"
        assert 'error' in data, "Should have error for nonexistent skill"

        Path(f.name).unlink()


# =============================================================================
# Analyze Subcommand Tests
# =============================================================================

def test_analyze_help():
    """Test analyze --help is available."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    assert 'component' in result.stdout or 'component' in result.stderr, \
        "Help should mention component option"


def test_analyze_missing_component():
    """Test analyze requires component."""
    result = run_script(SCRIPT_PATH, 'analyze')
    assert result.returncode != 0, "Should error without component"


def test_analyze_nonexistent_file():
    """Test analyze handles nonexistent file."""
    result = run_script(SCRIPT_PATH, 'analyze', '--component', '/nonexistent/file.md')
    data = result.json()
    assert data is not None, "Should return valid JSON"
    assert 'error' in data, "Should have error for nonexistent file"


def test_analyze_valid_agent():
    """Test analyze with a valid agent file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, dir='/tmp'):
        # Create in a path that looks like agents/
        agent_dir = Path('/tmp/test_agents')
        agent_dir.mkdir(exist_ok=True)
        agent_file = agent_dir / 'test-agent.md'
        agent_file.write_text('---\nname: test-agent\ndescription: Test agent\ntools: Read, Write\n---\n\n# Test Agent\n\n## Purpose\nDoes testing.\n')

        result = run_script(SCRIPT_PATH, 'analyze', '--component', str(agent_file))
        data = result.json()
        assert data is not None, "Should return valid JSON"
        assert 'quality_score' in data, "Should have quality_score"

        agent_file.unlink()
        agent_dir.rmdir()


def test_analyze_real_agent():
    """Test analyze on a real agent file."""
    agent_file = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'agents' / 'plugin-specify-agent.md'
    if not agent_file.exists():
        return  # Skip if not found

    result = run_script(SCRIPT_PATH, 'analyze', '--component', str(agent_file))
    data = result.json()
    assert data is not None, "Should return valid JSON"
    assert 'quality_score' in data, "Should have quality_score"
    assert data['quality_score'] >= 0, "Quality score should be non-negative"


# =============================================================================
# Readme Subcommand Tests
# =============================================================================

def test_readme_help():
    """Test readme --help is available."""
    result = run_script(SCRIPT_PATH, 'readme', '--help')
    assert 'bundle-path' in result.stdout or 'bundle-path' in result.stderr, \
        "Help should mention bundle-path option"


def test_readme_missing_path():
    """Test readme requires bundle-path."""
    result = run_script(SCRIPT_PATH, 'readme')
    assert result.returncode != 0, "Should error without bundle-path"


def test_readme_nonexistent_path():
    """Test readme handles nonexistent path."""
    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', '/nonexistent/bundle')
    data = result.json()
    assert data is not None, "Should return valid JSON"
    assert 'error' in data, "Should have error for nonexistent path"


def test_readme_real_bundle():
    """Test readme on a real bundle."""
    bundle_path = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development'
    if not bundle_path.exists():
        return  # Skip if not found

    result = run_script(SCRIPT_PATH, 'readme', '--bundle-path', str(bundle_path))
    data = result.json()
    assert data is not None, "Should return valid JSON"
    assert 'readme_generated' in data, "Should have readme_generated field"
    assert data['readme_generated'] is True, "Should successfully generate README"
    assert 'readme_content' in data, "Should have readme_content"


# =============================================================================
# Main
# =============================================================================
