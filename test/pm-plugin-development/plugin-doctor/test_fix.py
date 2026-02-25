#!/usr/bin/env python3
"""Tests for fix.py - consolidated plugin fix tools.

Tests plugin component fix capabilities including:
- extract: Extract fixable issues from diagnosis
- categorize: Categorize fixes as safe/risky
- apply: Apply a single fix
- verify: Verify a fix was applied
"""

import json
import tempfile
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_fix.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'fix'


# =============================================================================
# Main help tests
# =============================================================================


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'extract' in combined, 'extract subcommand in help'
    assert 'categorize' in combined, 'categorize subcommand in help'
    assert 'apply' in combined, 'apply subcommand in help'
    assert 'verify' in combined, 'verify subcommand in help'


# =============================================================================
# Extract Subcommand Tests
# =============================================================================


def test_extract_help():
    """Test extract --help is available."""
    result = run_script(SCRIPT_PATH, 'extract', '--help')
    assert 'input' in result.stdout or 'input' in result.stderr, 'Help should mention input option'


def test_extract_from_stdin():
    """Test extract accepts JSON from stdin."""
    diagnosis = {
        'issues': [
            {'type': 'missing-frontmatter', 'severity': 'high', 'fixable': True},
            {'type': 'bloat', 'severity': 'medium', 'fixable': False},
        ]
    }
    result = run_script(SCRIPT_PATH, 'extract', input_data=json.dumps(diagnosis))
    data = result.json()
    assert data is not None, 'Should return valid JSON'
    assert 'fixable_issues' in data or 'issues' in data, 'Should have issues field'


# =============================================================================
# Categorize Subcommand Tests
# =============================================================================


def test_categorize_help():
    """Test categorize --help is available."""
    result = run_script(SCRIPT_PATH, 'categorize', '--help')
    assert 'input' in result.stdout or 'input' in result.stderr, 'Help should mention input option'


def test_categorize_safe_issues():
    """Test categorize identifies safe fixes."""
    issues = {
        'issues': [
            {'type': 'missing-frontmatter', 'file': 'test.md'},
            {'type': 'trailing-whitespace', 'file': 'test.md'},
        ]
    }
    result = run_script(SCRIPT_PATH, 'categorize', input_data=json.dumps(issues))
    data = result.json()
    assert data is not None, 'Should return valid JSON'
    # Should have safe_fixes or similar field
    assert 'safe_fixes' in data or 'safe' in data or 'categorized' in data, 'Should categorize fixes'


# =============================================================================
# Apply Subcommand Tests
# =============================================================================


def test_apply_help():
    """Test apply --help is available."""
    result = run_script(SCRIPT_PATH, 'apply', '--help')
    combined = result.stdout + result.stderr
    assert 'fix' in combined.lower(), 'Help should mention fix option'


def test_apply_missing_arguments():
    """Test apply requires fix and bundle-dir."""
    result = run_script(SCRIPT_PATH, 'apply')
    assert result.returncode != 0, 'Should error without arguments'


# =============================================================================
# Verify Subcommand Tests
# =============================================================================


def test_verify_help():
    """Test verify --help is available."""
    result = run_script(SCRIPT_PATH, 'verify', '--help')
    combined = result.stdout + result.stderr
    assert 'fix-type' in combined or 'file' in combined, 'Help should mention fix-type or file option'


def test_verify_missing_arguments():
    """Test verify requires arguments."""
    result = run_script(SCRIPT_PATH, 'verify')
    assert result.returncode != 0, 'Should error without arguments'


def test_verify_with_valid_file():
    """Test verify with a valid file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'missing-frontmatter', '--file', f.name)
        data = result.json()
        assert data is not None, 'Should return valid JSON'

        Path(f.name).unlink()


# =============================================================================
# Rule 11 Apply Tests
# =============================================================================


def test_apply_rule_11_fix():
    """Test applying Rule 11 fix appends Skill to tools."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent_file = Path(tmp_dir) / 'test-agent.md'
        agent_file.write_text('---\nname: test-agent\ndescription: Test\ntools: Read, Write\n---\n\n# Test Agent\n')

        fix_json = json.dumps({'type': 'agent-skill-tool-visibility', 'file': 'test-agent.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is True, f'Fix should succeed: {data}'

        # Verify Skill was appended
        content = agent_file.read_text()
        assert 'Skill' in content, 'File should contain Skill after fix'
        assert 'tools: Read, Write, Skill' in content, f'Tools should have Skill appended: {content}'


def test_apply_rule_11_fix_already_present():
    """Test applying Rule 11 fix when Skill already present returns failure."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent_file = Path(tmp_dir) / 'test-agent.md'
        agent_file.write_text('---\nname: test-agent\ndescription: Test\ntools: Read, Skill\n---\n\n# Test Agent\n')

        fix_json = json.dumps({'type': 'agent-skill-tool-visibility', 'file': 'test-agent.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is False, 'Fix should fail when Skill already present'


# =============================================================================
# Rule 11 Verify Tests
# =============================================================================


def test_verify_rule_11_fixed():
    """Test verify reports resolved after Skill is added."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\ntools: Read, Write, Skill\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'agent-skill-tool-visibility', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_rule_11_still_missing():
    """Test verify reports not resolved when Skill still missing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\ntools: Read, Write\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'agent-skill-tool-visibility', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


def test_verify_rule_11_no_tools_field():
    """Test verify reports resolved when no tools field (inherits all)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'agent-skill-tool-visibility', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is True, f'Issue should be resolved (no tools = inherits all): {data}'

        Path(f.name).unlink()


# =============================================================================
# Apply unsupported-skill-tools-field Tests
# =============================================================================


def test_apply_remove_unsupported_tools_field():
    """Test applying unsupported-skill-tools-field fix removes allowed-tools."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nallowed-tools: Read, Grep\nuser-invokable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'allowed-tools' not in content, f'allowed-tools should be removed: {content}'
        assert 'user-invokable: true' in content, 'Other fields should be preserved'
        assert 'name: test-skill' in content, 'Name field should be preserved'


def test_apply_remove_unsupported_tools_field_with_tools():
    """Test applying unsupported-skill-tools-field fix removes tools: field."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\ntools: Read\nuser-invokable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'tools:' not in content, f'tools field should be removed: {content}'


def test_apply_remove_unsupported_tools_no_field():
    """Test applying unsupported-skill-tools-field fix when field absent fails gracefully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is False, 'Fix should fail when field not present'


# =============================================================================
# Apply misspelled-user-invokable Tests
# =============================================================================


def test_apply_rename_misspelled_user_invokable():
    """Test applying misspelled-user-invokable fix renames user-invocable."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'misspelled-user-invokable', 'file': 'SKILL.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'user-invokable: true' in content, f'Should rename to user-invokable: {content}'
        assert 'user-invocable' not in content, f'Misspelled field should be gone: {content}'


def test_apply_rename_misspelled_user_invokable_not_present():
    """Test applying misspelled-user-invokable fix when not misspelled fails gracefully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'misspelled-user-invokable', 'file': 'SKILL.md'})
        result = run_script(SCRIPT_PATH, 'apply', '--fix', '-', '--bundle-dir', tmp_dir, input_data=fix_json)
        data = result.json()
        assert data['success'] is False, 'Fix should fail when not misspelled'


# =============================================================================
# Verify unsupported-skill-tools-field Tests
# =============================================================================


def test_verify_unsupported_tools_resolved():
    """Test verify reports resolved after allowed-tools removed."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'unsupported-skill-tools-field', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_unsupported_tools_still_present():
    """Test verify reports not resolved when allowed-tools still present."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nallowed-tools: Read\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'unsupported-skill-tools-field', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


# =============================================================================
# Verify misspelled-user-invokable Tests
# =============================================================================


def test_verify_misspelled_user_invokable_resolved():
    """Test verify reports resolved after user-invocable renamed."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'misspelled-user-invokable', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_misspelled_user_invokable_still_present():
    """Test verify reports not resolved when user-invocable still misspelled."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'misspelled-user-invokable', '--file', f.name)
        data = result.json()
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


# =============================================================================
# Main
# =============================================================================
