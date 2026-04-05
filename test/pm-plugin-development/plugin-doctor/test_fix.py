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
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_fix.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'fix'

# Direct imports for Tier 2 testing
from _cmd_apply import cmd_apply  # noqa: E402
from _cmd_categorize import cmd_categorize  # noqa: E402
from _cmd_extract import cmd_extract  # noqa: E402
from _cmd_verify import cmd_verify  # noqa: E402

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
    assert 'extract' in combined, 'extract subcommand in help'
    assert 'categorize' in combined, 'categorize subcommand in help'
    assert 'apply' in combined, 'apply subcommand in help'
    assert 'verify' in combined, 'verify subcommand in help'


def test_apply_missing_arguments():
    """Test apply requires fix and bundle-dir."""
    result = run_script(SCRIPT_PATH, 'apply')
    assert result.returncode != 0, 'Should error without arguments'


# =============================================================================
# Extract Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_extract_from_stdin():
    """Test extract accepts JSON diagnosis data."""
    diagnosis = {
        'issues': [
            {'type': 'missing-frontmatter', 'severity': 'high', 'fixable': True},
            {'type': 'bloat', 'severity': 'medium', 'fixable': False},
        ]
    }
    # Write to temp file for input
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(diagnosis, f)
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_extract(args)
        assert data is not None, 'Should return valid dict'
        assert 'fixable_issues' in data or 'issues' in data, 'Should have issues field'
        Path(f.name).unlink()


# =============================================================================
# Categorize Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_categorize_safe_issues():
    """Test categorize identifies safe fixes."""
    issues = {
        'fixable_issues': [
            {'type': 'checklist-pattern', 'file': 'test.md'},
            {'type': 'subdoc-checklist-pattern', 'file': 'ref.md'},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(issues, f)
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_categorize(args)
        assert data is not None, 'Should return valid dict'
        assert 'safe' in data or 'safe_fixes' in data or 'categorized' in data, 'Should categorize fixes'
        Path(f.name).unlink()


# =============================================================================
# Verify Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_with_valid_file():
    """Test verify with a valid file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='missing-frontmatter', file=f.name)
        data = cmd_verify(args)
        assert data is not None, 'Should return valid dict'

        Path(f.name).unlink()


# =============================================================================
# Rule 11 Apply Tests (Tier 2 - direct import)
# =============================================================================


def test_apply_rule_11_fix():
    """Test applying Rule 11 fix appends Skill to tools."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent_file = Path(tmp_dir) / 'test-agent.md'
        agent_file.write_text('---\nname: test-agent\ndescription: Test\ntools: Read, Write\n---\n\n# Test Agent\n')

        fix_json = json.dumps({'type': 'agent-skill-tool-visibility', 'file': 'test-agent.md'})
        # Write fix to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is False, 'Fix should fail when Skill already present'


# =============================================================================
# Rule 11 Verify Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_rule_11_fixed():
    """Test verify reports resolved after Skill is added."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\ntools: Read, Write, Skill\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='agent-skill-tool-visibility', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_rule_11_still_missing():
    """Test verify reports not resolved when Skill still missing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\ntools: Read, Write\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='agent-skill-tool-visibility', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


def test_verify_rule_11_no_tools_field():
    """Test verify reports resolved when no tools field (inherits all)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='agent-skill-tool-visibility', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved (no tools = inherits all): {data}'

        Path(f.name).unlink()


# =============================================================================
# Apply unsupported-skill-tools-field Tests (Tier 2 - direct import)
# =============================================================================


def test_apply_remove_unsupported_tools_field():
    """Test applying unsupported-skill-tools-field fix removes allowed-tools."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text(
            '---\nname: test-skill\ndescription: Test\nallowed-tools: Read, Grep\nuser-invocable: true\n---\n\n# Test\n'
        )

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'allowed-tools' not in content, f'allowed-tools should be removed: {content}'
        assert 'user-invocable: true' in content, 'Other fields should be preserved'
        assert 'name: test-skill' in content, 'Name field should be preserved'


def test_apply_remove_unsupported_tools_field_with_tools():
    """Test applying unsupported-skill-tools-field fix removes tools: field."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text(
            '---\nname: test-skill\ndescription: Test\ntools: Read\nuser-invocable: true\n---\n\n# Test\n'
        )

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'tools:' not in content, f'tools field should be removed: {content}'


def test_apply_remove_unsupported_tools_no_field():
    """Test applying unsupported-skill-tools-field fix when field absent fails gracefully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'unsupported-skill-tools-field', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is False, 'Fix should fail when field not present'


# =============================================================================
# Apply misspelled-user-invocable Tests (Tier 2 - direct import)
# =============================================================================


def test_apply_rename_misspelled_user_invocable():
    """Test applying misspelled-user-invocable fix renames user-invokable."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'misspelled-user-invocable', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = skill_file.read_text()
        assert 'user-invocable: true' in content, f'Should rename to user-invocable: {content}'
        assert 'user-invokable' not in content, f'Misspelled field should be gone: {content}'


def test_apply_rename_misspelled_user_invocable_not_present():
    """Test applying misspelled-user-invocable fix when not misspelled fails gracefully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / 'SKILL.md'
        skill_file.write_text('---\nname: test-skill\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')

        fix_json = json.dumps({'type': 'misspelled-user-invocable', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is False, 'Fix should fail when not misspelled'


# =============================================================================
# Verify unsupported-skill-tools-field Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_unsupported_tools_resolved():
    """Test verify reports resolved after allowed-tools removed."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='unsupported-skill-tools-field', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_unsupported_tools_still_present():
    """Test verify reports not resolved when allowed-tools still present."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nallowed-tools: Read\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='unsupported-skill-tools-field', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


# =============================================================================
# Verify misspelled-user-invocable Tests (Tier 2 - direct import)
# =============================================================================


def test_verify_misspelled_user_invocable_resolved():
    """Test verify reports resolved after user-invokable renamed."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invocable: true\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='misspelled-user-invocable', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is True, f'Issue should be resolved: {data}'

        Path(f.name).unlink()


def test_verify_misspelled_user_invocable_still_present():
    """Test verify reports not resolved when user-invocable still misspelled."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\nuser-invokable: true\n---\n\n# Test\n')
        f.flush()

        args = Namespace(fix_type='misspelled-user-invocable', file=f.name)
        data = cmd_verify(args)
        assert data['issue_resolved'] is False, f'Issue should NOT be resolved: {data}'

        Path(f.name).unlink()


# =============================================================================
# Apply checklist-pattern Tests (Tier 2 - direct import)
# =============================================================================


def test_checklist_pattern_is_safe():
    """Test checklist-pattern is categorized as safe fix."""
    issues = {
        'fixable_issues': [
            {'type': 'checklist-pattern', 'file': 'test.md'},
            {'type': 'subdoc-checklist-pattern', 'file': 'ref.md'},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(issues, f)
        f.flush()
        args = Namespace(input=f.name)
        data = cmd_categorize(args)
        Path(f.name).unlink()

    safe = data.get('safe', [])
    safe_types = [fix.get('type') for fix in safe]
    assert 'checklist-pattern' in safe_types, f'checklist-pattern should be safe, got {safe_types}'
    assert 'subdoc-checklist-pattern' in safe_types, f'subdoc-checklist-pattern should be safe, got {safe_types}'


def test_apply_checklist_pattern_fix():
    """Test applying checklist-pattern fix removes - [ ] markers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = Path(tmp_dir) / 'SKILL.md'
        md_file.write_text('---\nname: test\n---\n\n# Test\n\n- [ ] First item\n- [ ] Second item\n- Normal item\n')

        fix_json = json.dumps({'type': 'checklist-pattern', 'file': 'SKILL.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = md_file.read_text()
        assert '- [ ]' not in content, f'Checkboxes should be removed: {content}'
        assert '- First item' in content, 'List items should be preserved'
        assert '- Normal item' in content, 'Non-checkbox items should be unchanged'


def test_apply_checklist_pattern_fix_mixed():
    """Test applying checklist-pattern fix removes both [ ] and [x] markers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = Path(tmp_dir) / 'test.md'
        md_file.write_text('# Test\n\n- [ ] Unchecked\n- [x] Checked\n- [X] Also checked\n')

        fix_json = json.dumps({'type': 'subdoc-checklist-pattern', 'file': 'test.md'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(fix_json)
            f.flush()
            args = Namespace(fix=f.name, bundle_dir=tmp_dir)
            data = cmd_apply(args)
            Path(f.name).unlink()

        assert data['success'] is True, f'Fix should succeed: {data}'

        content = md_file.read_text()
        assert '[ ]' not in content, 'Unchecked boxes should be removed'
        assert '[x]' not in content, 'Checked boxes should be removed'
        assert '- Unchecked' in content, 'List text should be preserved'
        assert '- Checked' in content, 'List text should be preserved'
        assert '- Also checked' in content, 'List text should be preserved'


# =============================================================================
# Main
# =============================================================================
