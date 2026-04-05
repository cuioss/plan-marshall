#!/usr/bin/env python3
"""Tests for cmd_validate.py and cmd_generate.py via component.py entry point.

Covers edge cases and error handling not present in test_component.py:
- validate: file not found, skill prohibited fields, content-level validation
- generate: invalid JSON, missing required fields, type validation
"""

import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-create', 'component.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'

# Direct imports for Tier 2 testing
from cmd_generate import cmd_generate  # noqa: E402
from cmd_validate import cmd_validate  # noqa: E402

# =============================================================================
# CLI plumbing tests (Tier 3 - subprocess)
# =============================================================================


def test_no_subcommand_fails():
    """Running without subcommand fails."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode != 0


def test_validate_file_not_found_cli():
    """Validate returns error via CLI when file does not exist."""
    result = run_script(SCRIPT_PATH, 'validate', '--file', '/nonexistent/file.md', '--type', 'agent')
    data = result.toon()
    assert data['valid'] is False


# =============================================================================
# Validate: file-not-found and read errors (Tier 2 - direct import)
# =============================================================================


def test_validate_file_not_found():
    """Validate returns error dict when file does not exist."""
    args = Namespace(file='/nonexistent/file.md', type='agent', command='validate')
    data = cmd_validate(args)
    assert data['valid'] is False
    assert any(e['type'] == 'file_not_found' for e in data['errors'])


def test_validate_skill_with_prohibited_tools_field():
    """Validate skill rejects tools in frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: bad-skill\ndescription: Has tools\ntools: Read, Write\n---\n\n# Bad Skill\n')
        f.flush()
        args = Namespace(file=f.name, type='skill', command='validate')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any(e['type'] == 'prohibited_field' and e['field'] == 'tools' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_skill_with_prohibited_model_field():
    """Validate skill rejects model in frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: bad-skill\ndescription: Has model\nmodel: sonnet\n---\n\n# Bad Skill\n')
        f.flush()
        args = Namespace(file=f.name, type='skill', command='validate')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any(e['type'] == 'prohibited_field' and e['field'] == 'model' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_agent_missing_name_and_description():
    """Validate agent with missing required fields reports both errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\ntools: Read, Write\n---\n\n# No Name Agent\n')
        f.flush()
        args = Namespace(file=f.name, type='agent', command='validate')
        data = cmd_validate(args)
        assert data['valid'] is False
        missing_fields = [e['field'] for e in data['errors'] if e['type'] == 'frontmatter_field_missing']
        assert 'name' in missing_fields
        assert 'description' in missing_fields
        Path(f.name).unlink()


def test_validate_agent_missing_tools():
    """Validate agent without tools field is invalid."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: no-tools\ndescription: Missing tools\n---\n\n# No Tools\n')
        f.flush()
        args = Namespace(file=f.name, type='agent', command='validate')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any(e['field'] == 'tools' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_command_with_tools_warning():
    """Validate command with tools field gets a warning."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(
            '---\nname: cmd-with-tools\ndescription: Has tools\ntools: Read\n---\n\n'
            '# Command\n\n## WORKFLOW\n\nDo stuff.\n\n## USAGE EXAMPLES\n\nExample.\n'
        )
        f.flush()
        args = Namespace(file=f.name, type='command', command='validate')
        data = cmd_validate(args)
        assert any(w['type'] == 'unexpected_field' and w['field'] == 'tools' for w in data['warnings'])
        Path(f.name).unlink()


def test_validate_command_missing_workflow_section():
    """Validate command without WORKFLOW section is invalid."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(
            '---\nname: no-workflow\ndescription: Missing workflow\n---\n\n# Command\n\n## USAGE EXAMPLES\n\nExample.\n'
        )
        f.flush()
        args = Namespace(file=f.name, type='command', command='validate')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any('WORKFLOW' in e.get('message', '') for e in data['errors'])
        Path(f.name).unlink()


def test_validate_valid_skill_returns_true():
    """Validate a well-formed skill returns valid=True."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(
            '---\nname: good-skill\ndescription: A good skill\nuser-invocable: True\n---\n\n'
            '# Good Skill\n\n## What This Skill Provides\n\nStuff.\n\n'
            '## When to Use\n\nAlways.\n\n## Workflow\n\nDo things.\n'
        )
        f.flush()
        args = Namespace(file=f.name, type='skill', command='validate')
        data = cmd_validate(args)
        assert data['valid'] is True
        Path(f.name).unlink()


# =============================================================================
# Generate: error handling (Tier 2 - direct import)
# =============================================================================


def test_generate_invalid_json():
    """Generate with malformed JSON returns error."""
    args = Namespace(type='agent', config='not-json', command='generate')
    data = cmd_generate(args)
    assert data.get('status') == 'error'
    assert 'Invalid JSON' in data.get('message', '') or 'invalid_json' in data.get('error', '')


def test_generate_agent_missing_tools():
    """Generate agent without tools raises error."""
    args = Namespace(type='agent', config='{"name": "no-tools", "description": "Missing tools"}', command='generate')
    data = cmd_generate(args)
    assert data.get('status') == 'error'
    assert 'tools' in data.get('message', '').lower()


def test_generate_agent_empty_tools():
    """Generate agent with empty tools array raises error."""
    args = Namespace(
        type='agent',
        config='{"name": "empty-tools", "description": "Empty tools", "tools": []}',
        command='generate',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'error'
    assert 'at least one' in data.get('message', '').lower() or 'error' in str(data).lower()


def test_generate_command_basic():
    """Generate command produces frontmatter without tools."""
    args = Namespace(type='command', config='{"name": "my-cmd", "description": "A command"}', command='generate')
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'name: my-cmd' in content
    assert 'tools:' not in content


def test_generate_skill_defaults_user_invocable_false():
    """Generate skill defaults user-invocable to False."""
    args = Namespace(type='skill', config='{"name": "my-skill", "description": "A skill"}', command='generate')
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'user-invocable: False' in content


def test_generate_skill_user_invocable_true():
    """Generate skill with user-invocable set to True."""
    args = Namespace(
        type='skill',
        config='{"name": "my-skill", "description": "A skill", "user-invocable": true}',
        command='generate',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'user-invocable: True' in content


def test_generate_agent_with_model():
    """Generate agent includes model when provided."""
    args = Namespace(
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"], "model": "opus"}',
        command='generate',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'model: opus' in content


def test_generate_agent_without_model():
    """Generate agent omits model when not provided."""
    args = Namespace(
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"]}',
        command='generate',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    lines = [line for line in content.split('\n') if line.strip().startswith('model:')]
    assert not lines, 'model field should not appear in output'


def test_generate_frontmatter_has_delimiters():
    """Generate output contains --- delimiters in frontmatter value."""
    args = Namespace(
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"]}',
        command='generate',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert '---' in content


def test_generate_special_chars_in_description():
    """Generate handles colons and quotes in description."""
    args = Namespace(
        type='agent',
        config='{"name": "a", "description": "A desc: with \\"quotes\\"", "tools": ["Read"]}',
        command='generate',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'description:' in content


# =============================================================================
# Main
# =============================================================================
