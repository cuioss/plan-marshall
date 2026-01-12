#!/usr/bin/env python3
"""Tests for component.py script.

Consolidated from:
- test_generate_frontmatter.py → generate subcommand tests
- test_validate_component.py → validate subcommand tests

Tests component frontmatter generation and validation.
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure
from conftest import run_script, TestRunner, get_script_path

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-create', 'component.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# =============================================================================
# Generate Subcommand Tests - Agent Frontmatter
# =============================================================================

def test_generate_agent_with_all_fields():
    """Test generate agent frontmatter with all fields."""
    fixture = FIXTURES_DIR / 'agent-answers-full.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', input_json)

    assert 'model: sonnet' in result.stdout, "Agent frontmatter should include model field"


def test_generate_agent_tools_comma_separated():
    """Test generate agent tools are comma-separated, not array syntax."""
    fixture = FIXTURES_DIR / 'agent-answers-full.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', input_json)

    import re
    has_comma_separated = re.search(r'tools: [A-Za-z]+(, [A-Za-z]+)*', result.stdout) is not None
    has_array_syntax = '[' in result.stdout

    assert has_comma_separated, "Tools should be comma-separated"
    assert not has_array_syntax, "Tools should not use array syntax"


def test_generate_agent_without_model():
    """Test generate agent without optional model field."""
    fixture = FIXTURES_DIR / 'agent-answers-no-model.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', input_json)

    assert 'name: test-agent' in result.stdout, "Agent frontmatter should include name"


def test_generate_agent_special_chars():
    """Test generate special characters in description are handled."""
    fixture = FIXTURES_DIR / 'agent-answers-special-chars.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', input_json)

    assert 'quotes' in result.stdout, "Should handle special characters in description"


# =============================================================================
# Generate Subcommand Tests - Command Frontmatter
# =============================================================================

def test_generate_command_no_tools():
    """Test generate command frontmatter has no tools field."""
    fixture = FIXTURES_DIR / 'command-answers.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'command', '--config', input_json)

    assert 'name: test-command' in result.stdout, "Command frontmatter should include name"
    assert 'tools:' not in result.stdout, "Command frontmatter should not have tools field"


# =============================================================================
# Generate Subcommand Tests - Skill Frontmatter
# =============================================================================

def test_generate_skill_with_tools():
    """Test generate skill with allowed-tools."""
    fixture = FIXTURES_DIR / 'skill-answers-with-tools.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'skill', '--config', input_json)

    assert 'allowed-tools: Read, Grep' in result.stdout, "Skill should have allowed-tools"


def test_generate_skill_without_tools():
    """Test generate skill without tools omits allowed-tools."""
    fixture = FIXTURES_DIR / 'skill-answers-no-tools.json'
    if not fixture.exists():
        return  # Skip if fixture not available

    input_json = fixture.read_text().strip()
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'skill', '--config', input_json)

    assert 'name: test-skill' in result.stdout, "Skill frontmatter should include name"
    assert 'allowed-tools:' not in result.stdout, "Skill without tools should omit allowed-tools"


# =============================================================================
# Generate Subcommand Tests - Error Handling
# =============================================================================

def test_generate_empty_tools_error():
    """Test generate empty tools array produces error or warning."""
    input_json = '{"name": "test", "description": "Test", "tools": []}'
    result = run_script(SCRIPT_PATH, 'generate', '--type', 'agent', '--config', input_json)

    output = result.stdout.lower() + result.stderr.lower()
    has_error = 'error' in output or 'warning' in output or 'at least one' in output
    assert has_error, "Should error or warn on empty tools array"


# =============================================================================
# Validate Subcommand Tests
# =============================================================================

def test_validate_valid_agent():
    """Test validate valid agent validation."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'valid-agent.md'),
        '--type', 'agent'
    )
    data = result.json()
    assert data.get('valid') is True, "Valid agent validation"


def test_validate_agent_no_model():
    """Test validate valid agent without model."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'valid-agent-no-model.md'),
        '--type', 'agent'
    )
    data = result.json()
    assert data.get('valid') is True, "Valid agent without model"


def test_validate_agent_prohibited_task_tool():
    """Test validate agent with prohibited Task tool is invalid."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'invalid-agent-task-tool.md'),
        '--type', 'agent'
    )
    data = result.json()
    assert data.get('valid') is False, "Agent with prohibited Task tool should be invalid"


def test_validate_agent_self_invocation():
    """Test validate agent with self-invocation pattern is invalid."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'invalid-agent-self-invoke.md'),
        '--type', 'agent'
    )
    data = result.json()
    assert data.get('valid') is False, "Agent with self-invocation should be invalid"


def test_validate_agent_missing_frontmatter():
    """Test validate agent missing frontmatter is invalid."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'invalid-agent-no-frontmatter.md'),
        '--type', 'agent'
    )
    data = result.json()
    assert data.get('valid') is False, "Agent missing frontmatter should be invalid"


def test_validate_valid_command():
    """Test validate valid command validation."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'valid-command.md'),
        '--type', 'command'
    )
    data = result.json()
    assert data.get('valid') is True, "Valid command validation"


def test_validate_command_missing_workflow():
    """Test validate command missing WORKFLOW section is invalid."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'invalid-command-missing-section.md'),
        '--type', 'command'
    )
    data = result.json()
    assert data.get('valid') is False, "Command missing WORKFLOW should be invalid"


def test_validate_valid_skill():
    """Test validate valid skill validation."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'valid-skill.md'),
        '--type', 'skill'
    )
    data = result.json()
    assert data.get('valid') is True, "Valid skill validation"


def test_validate_skill_bad_frontmatter():
    """Test validate skill with bad frontmatter is invalid."""
    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--file', str(FIXTURES_DIR / 'invalid-skill-bad-frontmatter.md'),
        '--type', 'skill'
    )
    data = result.json()
    assert data.get('valid') is False, "Skill with bad frontmatter should be invalid"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Generate subcommand tests
        test_generate_agent_with_all_fields,
        test_generate_agent_tools_comma_separated,
        test_generate_agent_without_model,
        test_generate_agent_special_chars,
        test_generate_command_no_tools,
        test_generate_skill_with_tools,
        test_generate_skill_without_tools,
        test_generate_empty_tools_error,
        # Validate subcommand tests
        test_validate_valid_agent,
        test_validate_agent_no_model,
        test_validate_agent_prohibited_task_tool,
        test_validate_agent_self_invocation,
        test_validate_agent_missing_frontmatter,
        test_validate_valid_command,
        test_validate_command_missing_workflow,
        test_validate_valid_skill,
        test_validate_skill_bad_frontmatter,
    ])
    sys.exit(runner.run())
