#!/usr/bin/env python3
"""Tests for component.py script.

Consolidated from:
- test_generate_frontmatter.py -> generate subcommand tests
- test_validate_component.py -> validate subcommand tests

Tests component frontmatter generation and validation.
"""

from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-create', 'component.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'

# Direct imports for Tier 2 testing
from cmd_generate import cmd_generate  # noqa: E402
from cmd_validate import cmd_validate  # noqa: E402

# =============================================================================
# CLI plumbing tests (Tier 3 - subprocess)
# =============================================================================


def test_generate_agent_with_all_fields_cli():
    """Test generate agent frontmatter with all fields via CLI."""
    fixture = FIXTURES_DIR / 'agent-answers-full.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', input_json)
    assert 'model: sonnet' in result.stdout, 'Agent frontmatter should include model field'


def test_validate_valid_agent_cli():
    """Test validate valid agent via CLI."""
    result = run_script(SCRIPT_PATH, 'validate', '--file', str(FIXTURES_DIR / 'valid-agent.md'), '--type', 'agent')
    data = result.toon()
    assert data.get('valid') is True, 'Valid agent validation'


# =============================================================================
# Generate Subcommand Tests - Agent Frontmatter (Tier 2 - direct import)
# =============================================================================


def test_generate_agent_tools_comma_separated():
    """Test generate agent tools are comma-separated, not array syntax."""
    fixture = FIXTURES_DIR / 'agent-answers-full.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    args = Namespace(type='agent', config=input_json, command='generate')
    data = cmd_generate(args)

    import re

    content = data.get('frontmatter', '')
    has_comma_separated = re.search(r'tools: [A-Za-z]+(, [A-Za-z]+)*', content) is not None
    has_array_syntax = '[' in content

    assert has_comma_separated, 'Tools should be comma-separated'
    assert not has_array_syntax, 'Tools should not use array syntax'


def test_generate_agent_without_model():
    """Test generate agent without optional model field."""
    fixture = FIXTURES_DIR / 'agent-answers-no-model.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    args = Namespace(type='agent', config=input_json, command='generate')
    data = cmd_generate(args)
    content = data.get('frontmatter', '')
    assert 'name: test-agent' in content, 'Agent frontmatter should include name'


def test_generate_agent_special_chars():
    """Test generate special characters in description are handled."""
    fixture = FIXTURES_DIR / 'agent-answers-special-chars.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    args = Namespace(type='agent', config=input_json, command='generate')
    data = cmd_generate(args)
    content = data.get('frontmatter', '')
    assert 'quotes' in content, 'Should handle special characters in description'


# =============================================================================
# Generate Subcommand Tests - Command Frontmatter (Tier 2 - direct import)
# =============================================================================


def test_generate_command_no_tools():
    """Test generate command frontmatter has no tools field."""
    fixture = FIXTURES_DIR / 'command-answers.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    args = Namespace(type='command', config=input_json, command='generate')
    data = cmd_generate(args)
    content = data.get('frontmatter', '')
    assert 'name: test-command' in content, 'Command frontmatter should include name'
    assert 'tools:' not in content, 'Command frontmatter should not have tools field'


# =============================================================================
# Generate Subcommand Tests - Skill Frontmatter (Tier 2 - direct import)
# =============================================================================


def test_generate_skill_with_user_invocable():
    """Test generate skill includes user-invocable field."""
    fixture = FIXTURES_DIR / 'skill-answers-with-tools.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    args = Namespace(type='skill', config=input_json, command='generate')
    data = cmd_generate(args)
    content = data.get('frontmatter', '')
    assert 'user-invocable: True' in content, 'Skill should have user-invocable field'
    assert 'allowed-tools' not in content, 'Skill must not contain allowed-tools'
    assert 'tools:' not in content, 'Skill must not contain tools field'


def test_generate_skill_without_tools():
    """Test generate skill omits prohibited fields."""
    fixture = FIXTURES_DIR / 'skill-answers-no-tools.json'
    if not fixture.exists():
        return

    input_json = fixture.read_text().strip()
    args = Namespace(type='skill', config=input_json, command='generate')
    data = cmd_generate(args)
    content = data.get('frontmatter', '')
    assert 'name: test-skill' in content, 'Skill frontmatter should include name'
    assert 'allowed-tools:' not in content, 'Skill must not contain allowed-tools'
    assert 'user-invocable: False' in content, 'Skill should default user-invocable to False'


# =============================================================================
# Generate Subcommand Tests - Error Handling (Tier 2 - direct import)
# =============================================================================


def test_generate_empty_tools_error():
    """Test generate empty tools array produces error or warning."""
    args = Namespace(type='agent', config='{"name": "test", "description": "Test", "tools": []}', command='generate')
    data = cmd_generate(args)
    output = str(data).lower()
    has_error = 'error' in output or 'warning' in output or 'at least one' in output
    assert has_error, 'Should error or warn on empty tools array'


# =============================================================================
# Validate Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_validate_valid_agent():
    """Test validate valid agent validation."""
    args = Namespace(file=str(FIXTURES_DIR / 'valid-agent.md'), type='agent', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is True, 'Valid agent validation'


def test_validate_agent_no_model():
    """Test validate valid agent without model."""
    args = Namespace(file=str(FIXTURES_DIR / 'valid-agent-no-model.md'), type='agent', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is True, 'Valid agent without model'


def test_validate_agent_prohibited_task_tool():
    """Test validate agent with prohibited Task tool is invalid."""
    args = Namespace(file=str(FIXTURES_DIR / 'invalid-agent-task-tool.md'), type='agent', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is False, 'Agent with prohibited Task tool should be invalid'


def test_validate_agent_self_invocation():
    """Test validate agent with self-invocation pattern is invalid."""
    args = Namespace(file=str(FIXTURES_DIR / 'invalid-agent-self-invoke.md'), type='agent', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is False, 'Agent with self-invocation should be invalid'


def test_validate_agent_missing_frontmatter():
    """Test validate agent missing frontmatter is invalid."""
    args = Namespace(file=str(FIXTURES_DIR / 'invalid-agent-no-frontmatter.md'), type='agent', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is False, 'Agent missing frontmatter should be invalid'


def test_validate_valid_command():
    """Test validate valid command validation."""
    args = Namespace(file=str(FIXTURES_DIR / 'valid-command.md'), type='command', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is True, 'Valid command validation'


def test_validate_command_missing_workflow():
    """Test validate command missing WORKFLOW section is invalid."""
    args = Namespace(file=str(FIXTURES_DIR / 'invalid-command-missing-section.md'), type='command', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is False, 'Command missing WORKFLOW should be invalid'


def test_validate_valid_skill():
    """Test validate valid skill validation."""
    args = Namespace(file=str(FIXTURES_DIR / 'valid-skill.md'), type='skill', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is True, 'Valid skill validation'


def test_validate_skill_bad_frontmatter():
    """Test validate skill with bad frontmatter is invalid."""
    args = Namespace(file=str(FIXTURES_DIR / 'invalid-skill-bad-frontmatter.md'), type='skill', command='validate')
    data = cmd_validate(args)
    assert data.get('valid') is False, 'Skill with bad frontmatter should be invalid'


# =============================================================================
# Main
# =============================================================================
