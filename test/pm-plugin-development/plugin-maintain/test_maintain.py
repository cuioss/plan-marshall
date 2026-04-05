#!/usr/bin/env python3
"""Tests for maintain.py - consolidated plugin maintenance tools.

Tests plugin maintenance capabilities including:
- update: Apply updates to a component
- check-duplication: Check for duplicate knowledge
- analyze: Analyze component for quality
- readme: Generate README for a bundle
"""

import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-maintain', 'maintain.py')

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


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'update' in combined, 'update subcommand in help'
    assert 'check-duplication' in combined, 'check-duplication subcommand in help'
    assert 'analyze' in combined, 'analyze subcommand in help'
    assert 'readme' in combined, 'readme subcommand in help'


def test_update_missing_component():
    """Test update requires component."""
    result = run_script(SCRIPT_PATH, 'update')
    assert result.returncode != 0, 'Should error without component'


# =============================================================================
# Update Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_update_with_updates_arg():
    """Test update with --updates argument."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Original\n---\n\n# Test\n')
        f.flush()

        updates = '{"updates": [{"type": "frontmatter", "field": "version", "value": "1.0"}]}'
        args = Namespace(component=f.name, updates=updates)
        data = cmd_update(args)
        assert data is not None, 'Should return valid dict'

        # Clean up backup if created
        backup = Path(f.name + '.maintain-backup')
        if backup.exists():
            backup.unlink()
        Path(f.name).unlink()


# =============================================================================
# Check-Duplication Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_checkdup_nonexistent_skill():
    """Test check-duplication handles nonexistent skill path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('# Some content\n')
        f.flush()

        args = Namespace(skill_path='/nonexistent/skill', content_file=f.name)
        data = cmd_check_duplication(args)
        assert data is not None, 'Should return valid dict'
        assert 'error' in data, 'Should have error for nonexistent skill'

        Path(f.name).unlink()


# =============================================================================
# Analyze Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_analyze_nonexistent_file():
    """Test analyze handles nonexistent file."""
    args = Namespace(component='/nonexistent/file.md')
    data = cmd_analyze(args)
    assert data is not None, 'Should return valid dict'
    assert 'error' in data, 'Should have error for nonexistent file'


def test_analyze_valid_agent():
    """Test analyze with a valid agent file."""
    agent_dir = Path('/tmp/test_agents')
    agent_dir.mkdir(exist_ok=True)
    agent_file = agent_dir / 'test-agent.md'
    agent_file.write_text(
        '---\nname: test-agent\ndescription: Test agent\ntools: Read, Write\n---\n\n# Test Agent\n\n## Purpose\nDoes testing.\n'
    )

    args = Namespace(component=str(agent_file))
    data = cmd_analyze(args)
    assert data is not None, 'Should return valid dict'
    assert 'quality_score' in data, 'Should have quality_score'

    agent_file.unlink()
    agent_dir.rmdir()


def test_analyze_real_agent():
    """Test analyze on a real agent file."""
    agent_file = (
        PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'agents' / 'plugin-specify-agent.md'
    )
    if not agent_file.exists():
        return  # Skip if not found

    args = Namespace(component=str(agent_file))
    data = cmd_analyze(args)
    assert data is not None, 'Should return valid dict'
    assert 'quality_score' in data, 'Should have quality_score'
    assert data['quality_score'] >= 0, 'Quality score should be non-negative'


# =============================================================================
# Readme Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_readme_nonexistent_path():
    """Test readme handles nonexistent path."""
    args = Namespace(bundle_path='/nonexistent/bundle')
    data = cmd_readme(args)
    assert data is not None, 'Should return valid dict'
    assert 'error' in data, 'Should have error for nonexistent path'


def test_readme_real_bundle():
    """Test readme on a real bundle."""
    bundle_path = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development'
    if not bundle_path.exists():
        return  # Skip if not found

    args = Namespace(bundle_path=str(bundle_path))
    data = cmd_readme(args)
    assert data is not None, 'Should return valid dict'
    assert 'readme_generated' in data, 'Should have readme_generated field'
    assert data['readme_generated'] is True, 'Should successfully generate README'
    assert 'readme_content' in data, 'Should have readme_content'


# =============================================================================
# Main
# =============================================================================
