#!/usr/bin/env python3
"""Tests for cmd_validate.py and cmd_generate.py via component.py entry point.

Covers edge cases and error handling not present in test_component.py:
- validate: file not found, skill prohibited fields, content-level validation
- generate: invalid JSON, missing required fields, type validation
"""

import tempfile
from pathlib import Path

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-create', 'component.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# =============================================================================
# Validate: file-not-found and read errors
# =============================================================================


def test_validate_file_not_found():
    """Validate returns error JSON when file does not exist."""
    result = run_script(SCRIPT_PATH, 'validate', '--file', '/nonexistent/file.md', '--type', 'agent')
    data = result.json()
    assert data['valid'] is False
    assert any(e['type'] == 'file_not_found' for e in data['errors'])


def test_validate_skill_with_prohibited_tools_field():
    """Validate skill rejects tools in frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: bad-skill\ndescription: Has tools\ntools: Read, Write\n---\n\n# Bad Skill\n')
        f.flush()
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'skill')
        data = result.json()
        assert data['valid'] is False
        assert any(e['type'] == 'prohibited_field' and e['field'] == 'tools' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_skill_with_prohibited_model_field():
    """Validate skill rejects model in frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: bad-skill\ndescription: Has model\nmodel: sonnet\n---\n\n# Bad Skill\n')
        f.flush()
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'skill')
        data = result.json()
        assert data['valid'] is False
        assert any(e['type'] == 'prohibited_field' and e['field'] == 'model' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_agent_missing_name_and_description():
    """Validate agent with missing required fields reports both errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\ntools: Read, Write\n---\n\n# No Name Agent\n')
        f.flush()
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'agent')
        data = result.json()
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
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'agent')
        data = result.json()
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
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'command')
        data = result.json()
        assert any(w['type'] == 'unexpected_field' and w['field'] == 'tools' for w in data['warnings'])
        Path(f.name).unlink()


def test_validate_command_missing_workflow_section():
    """Validate command without WORKFLOW section is invalid."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(
            '---\nname: no-workflow\ndescription: Missing workflow\n---\n\n'
            '# Command\n\n## USAGE EXAMPLES\n\nExample.\n'
        )
        f.flush()
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'command')
        data = result.json()
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
        result = run_script(SCRIPT_PATH, 'validate', '--file', f.name, '--type', 'skill')
        data = result.json()
        assert data['valid'] is True
        Path(f.name).unlink()


# =============================================================================
# Generate: error handling
# =============================================================================


def test_generate_invalid_json():
    """Generate with malformed JSON returns error."""
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', 'not-json')
    assert result.returncode != 0
    assert 'Invalid JSON' in result.stderr or 'error' in result.stderr.lower()


def test_generate_agent_missing_tools():
    """Generate agent without tools raises error."""
    config = '{"name": "no-tools", "description": "Missing tools"}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', config)
    assert result.returncode != 0
    assert 'tools' in result.stderr.lower()


def test_generate_agent_empty_tools():
    """Generate agent with empty tools array raises error."""
    config = '{"name": "empty-tools", "description": "Empty tools", "tools": []}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', config)
    assert result.returncode != 0
    assert 'at least one' in result.stderr.lower() or 'error' in result.stderr.lower()


def test_generate_command_basic():
    """Generate command produces frontmatter without tools."""
    config = '{"name": "my-cmd", "description": "A command"}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'command', '--config', config)
    assert result.returncode == 0
    assert 'name: my-cmd' in result.stdout
    assert 'tools:' not in result.stdout


def test_generate_skill_defaults_user_invocable_false():
    """Generate skill defaults user-invocable to False."""
    config = '{"name": "my-skill", "description": "A skill"}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'skill', '--config', config)
    assert result.returncode == 0
    assert 'user-invocable: False' in result.stdout


def test_generate_skill_user_invocable_true():
    """Generate skill with user-invocable set to True."""
    config = '{"name": "my-skill", "description": "A skill", "user-invocable": true}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'skill', '--config', config)
    assert result.returncode == 0
    assert 'user-invocable: True' in result.stdout


def test_generate_agent_with_model():
    """Generate agent includes model when provided."""
    config = '{"name": "a", "description": "b", "tools": ["Read"], "model": "opus"}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', config)
    assert result.returncode == 0
    assert 'model: opus' in result.stdout


def test_generate_agent_without_model():
    """Generate agent omits model when not provided."""
    config = '{"name": "a", "description": "b", "tools": ["Read"]}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', config)
    assert result.returncode == 0
    assert 'model:' not in result.stdout


def test_generate_frontmatter_has_delimiters():
    """Generate output is wrapped in --- delimiters."""
    config = '{"name": "a", "description": "b", "tools": ["Read"]}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', config)
    assert result.returncode == 0
    assert result.stdout.strip().startswith('---')
    assert result.stdout.strip().endswith('---')


def test_generate_special_chars_in_description():
    """Generate handles colons and quotes in description."""
    config = '{"name": "a", "description": "A desc: with \\"quotes\\"", "tools": ["Read"]}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', config)
    assert result.returncode == 0
    assert 'description:' in result.stdout


# =============================================================================
# No subcommand
# =============================================================================


def test_no_subcommand_fails():
    """Running without subcommand fails."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode != 0
