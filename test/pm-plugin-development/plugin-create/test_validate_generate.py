#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cmd_validate.py and cmd_generate.py via component.py entry point.

Covers edge cases and error handling not present in test_component.py:
- validate: file not found, skill prohibited fields, content-level validation
- generate: invalid JSON, missing required fields, type validation
"""

import json
import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, parse_ns, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-create', 'component.py')

# Argument namespaces come from the script's OWN parser, so each carries every
# default the real CLI applies. Parsed once at module scope: parse_ns
# re-executes the script module on every call.
_VALIDATE_NS = parse_ns(
    'pm-plugin-development', 'plugin-create', 'component.py',
    'validate', '--file', 'placeholder.md', '--type', 'skill', register=False,
)
_GENERATE_NS = parse_ns(
    'pm-plugin-development', 'plugin-create', 'component.py',
    'generate', '--type', 'skill', '--config', '{}', register=False,
)


def _ns(template: Namespace, **overrides) -> Namespace:
    """A parser-produced namespace with this test's values overlaid."""
    return Namespace(**{**vars(template), **overrides})
FIXTURES_DIR = Path(__file__).parent / 'fixtures'

# Direct imports for Tier 2 testing
import cmd_generate as _cmd_generate_mod  # noqa: E402
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
    args = _ns(_VALIDATE_NS, file='/nonexistent/file.md', type='agent')
    data = cmd_validate(args)
    assert data['valid'] is False
    assert any(e['type'] == 'file_not_found' for e in data['errors'])


def test_validate_skill_with_prohibited_tools_field():
    """Validate skill rejects tools in frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: bad-skill\ndescription: Has tools\ntools: Read, Write\n---\n\n# Bad Skill\n')
        f.flush()
        args = _ns(_VALIDATE_NS, file=f.name, type='skill')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any(e['type'] == 'prohibited_field' and e['field'] == 'tools' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_skill_with_prohibited_model_field():
    """Validate skill rejects model in frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: bad-skill\ndescription: Has model\nmodel: sonnet\n---\n\n# Bad Skill\n')
        f.flush()
        args = _ns(_VALIDATE_NS, file=f.name, type='skill')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any(e['type'] == 'prohibited_field' and e['field'] == 'model' for e in data['errors'])
        Path(f.name).unlink()


def test_validate_agent_missing_name_and_description():
    """Validate agent with missing required fields reports both errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\ntools: Read, Write\n---\n\n# No Name Agent\n')
        f.flush()
        args = _ns(_VALIDATE_NS, file=f.name, type='agent')
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
        args = _ns(_VALIDATE_NS, file=f.name, type='agent')
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
        args = _ns(_VALIDATE_NS, file=f.name, type='command')
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
        args = _ns(_VALIDATE_NS, file=f.name, type='command')
        data = cmd_validate(args)
        assert data['valid'] is False
        assert any('WORKFLOW' in e.get('message', '') for e in data['errors'])
        Path(f.name).unlink()


# =============================================================================
# Canonical-parser collapse: lenient frontmatter handling (Tier 2)
#
# ``cmd_validate`` now consumes the single canonical ``extract_frontmatter``
# (collapse-all decision). The old strict ``parse_simple_yaml`` validator —
# which RAISED on improper indentation and colon-less lines to emit
# ``invalid-yaml`` / ``improper-indentation`` findings — was deleted. The
# canonical flat parser handles those leniently instead. These tests pin the
# user-accepted behavior change: a frontmatter block that the old strict
# validator would have rejected as malformed is now parsed, and validation
# proceeds on the recovered fields rather than failing with a parse error.
# =============================================================================


def test_validate_lenient_parse_of_indented_frontmatter():
    """Improperly-indented keys are leniently parsed, not flagged as invalid YAML.

    The deleted strict validator raised ``Improper indentation detected`` for
    leading-space keys, surfacing a frontmatter parse error. The canonical
    parser strips the indentation and recovers the fields, so neither a
    ``frontmatter_missing`` error nor a ``frontmatter_field_missing`` for the
    recovered ``name``/``description`` is produced.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(
            '---\n  name: indented-skill\n  description: Has leading spaces\n---\n\n'
            '# Indented Skill\n\n## What This Skill Provides\n\nStuff.\n\n'
            '## When to Use\n\nAlways.\n\n## Workflow\n\nDo things.\n'
        )
        f.flush()
        args = _ns(_VALIDATE_NS, file=f.name, type='skill')
        data = cmd_validate(args)
        error_types = {e['type'] for e in data['errors']}
        assert 'frontmatter_missing' not in error_types
        missing_fields = {e.get('field') for e in data['errors'] if e['type'] == 'frontmatter_field_missing'}
        assert 'name' not in missing_fields
        assert 'description' not in missing_fields
        Path(f.name).unlink()


def test_validate_colonless_line_is_skipped_not_rejected():
    """A colon-less frontmatter line is skipped, not treated as a parse failure.

    The old strict validator raised ``Invalid YAML syntax`` for a line without
    a ``key: value`` shape. The canonical parser silently skips it, so the
    surrounding valid fields still drive validation.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(
            '---\nname: skip-skill\ndescription: A skill\na-stray-line-without-a-colon\n---\n\n'
            '# Skip Skill\n\n## What This Skill Provides\n\nStuff.\n\n'
            '## When to Use\n\nAlways.\n\n## Workflow\n\nDo things.\n'
        )
        f.flush()
        args = _ns(_VALIDATE_NS, file=f.name, type='skill')
        data = cmd_validate(args)
        error_types = {e['type'] for e in data['errors']}
        assert 'frontmatter_missing' not in error_types
        assert data['valid'] is True
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
        args = _ns(_VALIDATE_NS, file=f.name, type='skill')
        data = cmd_validate(args)
        assert data['valid'] is True
        Path(f.name).unlink()


# =============================================================================
# Generate: error handling (Tier 2 - direct import)
# =============================================================================


def test_generate_invalid_json():
    """Generate with malformed JSON returns error."""
    args = _ns(_GENERATE_NS, type='agent', config='not-json')
    data = cmd_generate(args)
    assert data.get('status') == 'error'
    assert 'Invalid JSON' in data.get('message', '') or 'invalid_json' in data.get('error', '')


def test_generate_agent_missing_tools():
    """Generate agent without tools raises error."""
    args = _ns(_GENERATE_NS, type='agent', config='{"name": "no-tools", "description": "Missing tools"}')
    data = cmd_generate(args)
    assert data.get('status') == 'error'
    assert 'tools' in data.get('message', '').lower()


def test_generate_agent_empty_tools():
    """Generate agent with empty tools array raises error."""
    args = _ns(
        _GENERATE_NS,
        type='agent',
        config='{"name": "empty-tools", "description": "Empty tools", "tools": []}',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'error'
    assert 'at least one' in data.get('message', '').lower() or 'error' in str(data).lower()


def test_generate_command_basic():
    """Generate command produces frontmatter without tools."""
    args = _ns(_GENERATE_NS, type='command', config='{"name": "my-cmd", "description": "A command"}')
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'name: my-cmd' in content
    assert 'tools:' not in content


def test_generate_skill_defaults_user_invocable_false():
    """Generate skill defaults user-invocable to False."""
    args = _ns(_GENERATE_NS, type='skill', config='{"name": "my-skill", "description": "A skill"}')
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'user-invocable: False' in content


def test_generate_skill_user_invocable_true():
    """Generate skill with user-invocable set to True."""
    args = _ns(
        _GENERATE_NS,
        type='skill',
        config='{"name": "my-skill", "description": "A skill", "user-invocable": true}',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'user-invocable: True' in content


def test_generate_agent_with_model():
    """Generate agent includes model when provided."""
    args = _ns(
        _GENERATE_NS,
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"], "model": "opus"}',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'model: opus' in content


def test_generate_agent_without_model():
    """Generate agent omits model when not provided."""
    args = _ns(
        _GENERATE_NS,
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"]}',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    lines = [line for line in content.split('\n') if line.strip().startswith('model:')]
    assert not lines, 'model field should not appear in output'


def test_generate_frontmatter_has_delimiters():
    """Generate output contains --- delimiters in frontmatter value."""
    args = _ns(
        _GENERATE_NS,
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"]}',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert '---' in content


def test_generate_special_chars_in_description():
    """Generate handles colons and quotes in description."""
    args = _ns(
        _GENERATE_NS,
        type='agent',
        config='{"name": "a", "description": "A desc: with \\"quotes\\"", "tools": ["Read"]}',
    )
    data = cmd_generate(args)
    assert data.get('status') == 'success'
    content = data.get('frontmatter', '')
    assert 'description:' in content


# =============================================================================
# Target-aware agent generation (D1)
# =============================================================================
# ``cmd_generate`` resolves the active runtime target the way the doctor's
# fixer does: on Claude an agent keeps the bare model alias (``model: sonnet``);
# on OpenCode it declares ``mode: subagent`` and a provider-qualified model id
# (``model: anthropic/...``). The active target is resolved via
# ``_doctor_shared.resolve_runtime_target`` (re-exported into cmd_generate).


def _generate_agent_with_model(monkeypatch, target, model='opus', tools=('Read',)):
    """Run agent generation under a fixed resolved target and return the frontmatter."""
    monkeypatch.setattr(_cmd_generate_mod, 'resolve_runtime_target', lambda: target)
    config = json.dumps({'name': 'a', 'description': 'b', 'tools': list(tools), 'model': model})
    args = _ns(_GENERATE_NS, type='agent', config=config)
    data = cmd_generate(args)
    return data.get('frontmatter', '')


def test_generate_agent_claude_keeps_bare_model_alias(monkeypatch):
    """On Claude, generated agent frontmatter keeps the bare model alias."""
    content = _generate_agent_with_model(monkeypatch, 'claude')
    assert 'mode: subagent' not in content, 'Claude agent must not declare OpenCode mode: subagent'
    assert 'model: opus' in content, f'Claude agent keeps the bare alias, got:\n{content}'
    assert 'anthropic/' not in content, 'Claude agent must not use a provider-qualified model id'


def test_generate_agent_opencode_declares_subagent_and_qualified_model(monkeypatch):
    """On OpenCode, generated agent frontmatter declares mode: subagent + a qualified model."""
    content = _generate_agent_with_model(monkeypatch, 'opencode')
    assert 'mode: subagent' in content, f'OpenCode agent should declare mode: subagent, got:\n{content}'
    assert 'model: anthropic/opus' in content, f'OpenCode agent should qualify the model, got:\n{content}'


def test_generate_agent_opencode_keeps_existing_qualified_model(monkeypatch):
    """An already provider-qualified model is not double-prefixed on OpenCode."""
    content = _generate_agent_with_model(monkeypatch, 'opencode', model='anthropic/claude-opus-4-8')
    assert 'model: anthropic/claude-opus-4-8' in content, f'Qualified model must pass through, got:\n{content}'


def test_generate_agent_opencode_without_model_still_declares_subagent(monkeypatch):
    """On OpenCode the subagent mode is declared even when no model is supplied."""
    monkeypatch.setattr(_cmd_generate_mod, 'resolve_runtime_target', lambda: 'opencode')
    args = _ns(
        _GENERATE_NS,
        type='agent',
        config='{"name": "a", "description": "b", "tools": ["Read"]}',
    )
    data = cmd_generate(args)
    content = data.get('frontmatter', '')
    assert 'mode: subagent' in content, f'OpenCode agent should declare mode: subagent, got:\n{content}'
    assert 'model:' not in content, f'No model supplied -> no model line, got:\n{content}'


def test_generate_command_and_skill_are_target_agnostic(monkeypatch):
    """Only agent generation is target-aware; command and skill output is target-neutral."""
    monkeypatch.setattr(_cmd_generate_mod, 'resolve_runtime_target', lambda: 'opencode')
    cmd_args = _ns(_GENERATE_NS, type='command', config='{"name": "c", "description": "d"}')
    cmd_content = cmd_generate(cmd_args).get('frontmatter', '')
    assert 'mode:' not in cmd_content, f'Command frontmatter carries no mode, got:\n{cmd_content}'

    skill_args = _ns(_GENERATE_NS, type='skill', config='{"name": "s", "description": "d"}')
    skill_content = cmd_generate(skill_args).get('frontmatter', '')
    assert 'mode:' not in skill_content, f'Skill frontmatter carries no mode, got:\n{skill_content}'


# =============================================================================
# Main
# =============================================================================
