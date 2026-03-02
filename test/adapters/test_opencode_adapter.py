"""Tests for the OpenCode adapter."""

import json
import shutil

import pytest
from marketplace.adapters.opencode_adapter import (
    MODEL_MAP,
    TOOL_NAME_MAP,
    TOOL_PERMISSION_MAP,
    OpenCodeAdapter,
    agent_uses_claude_only_tools,
    parse_frontmatter,
    transform_agent_frontmatter,
    transform_body,
    transform_command_frontmatter,
    transform_skill_frontmatter,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def adapter():
    return OpenCodeAdapter()


@pytest.fixture
def marketplace_dir(tmp_path):
    """Create a minimal marketplace structure for testing."""
    bundles = tmp_path / 'bundles'

    # Create a test bundle: test-bundle
    bundle = bundles / 'test-bundle'
    plugin_dir = bundle / '.claude-plugin'
    plugin_dir.mkdir(parents=True)

    # plugin.json
    plugin_json = {
        'name': 'test-bundle',
        'version': '0.1-BETA',
        'description': 'Test bundle for adapter testing',
        'skills': ['./skills/test-skill'],
        'agents': ['./agents/test-agent.md'],
        'commands': ['./commands/test-command.md'],
    }
    (plugin_dir / 'plugin.json').write_text(json.dumps(plugin_json))

    # Skill with standards subdirectory
    skill_dir = bundle / 'skills' / 'test-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\n'
        'name: test-skill\n'
        'description: A test skill for validation\n'
        'user-invocable: false\n'
        'allowed-tools: Read, Write, Grep\n'
        '---\n\n'
        '# Test Skill\n\n'
        'This is the body.\n\n'
        'Skill: other-bundle:other-skill\n\n'
        'Some more content.\n'
    )

    # Standards subdirectory
    standards_dir = skill_dir / 'standards'
    standards_dir.mkdir()
    (standards_dir / 'test-standard.md').write_text('# Test Standard\n\nContent here.\n')

    # References subdirectory
    refs_dir = skill_dir / 'references'
    refs_dir.mkdir()
    (refs_dir / 'test-ref.md').write_text('# Test Reference\n\nRef content.\n')

    # Scripts subdirectory
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir()
    (scripts_dir / 'test_script.py').write_text('#!/usr/bin/env python3\nprint("hello")\n')

    # Agent (no Claude-only tools)
    agents_dir = bundle / 'agents'
    agents_dir.mkdir(parents=True)
    (agents_dir / 'test-agent.md').write_text(
        '---\n'
        'name: test-agent\n'
        'description: A test agent\n'
        'tools: Read, Write, Grep\n'
        'model: sonnet\n'
        '---\n\n'
        '# Test Agent\n\n'
        'Agent body content.\n'
    )

    # Command
    commands_dir = bundle / 'commands'
    commands_dir.mkdir(parents=True)
    (commands_dir / 'test-command.md').write_text(
        '---\n'
        'name: test-command\n'
        'description: A test command\n'
        'allowed-tools: Read, Write, Bash\n'
        '---\n\n'
        '# Test Command\n\n'
        'Command body.\n'
    )

    # Create a second bundle with a Claude-only agent
    bundle2 = bundles / 'claude-heavy'
    plugin_dir2 = bundle2 / '.claude-plugin'
    plugin_dir2.mkdir(parents=True)
    plugin_json2 = {
        'name': 'claude-heavy',
        'version': '0.1-BETA',
        'description': 'Bundle with Claude-only agents',
        'skills': [],
        'agents': ['./agents/delegating-agent.md'],
        'commands': [],
    }
    (plugin_dir2 / 'plugin.json').write_text(json.dumps(plugin_json2))

    agents_dir2 = bundle2 / 'agents'
    agents_dir2.mkdir(parents=True)
    (agents_dir2 / 'delegating-agent.md').write_text(
        '---\n'
        'name: delegating-agent\n'
        'description: Agent that uses Task and Skill\n'
        'tools: Read, Write, Task, Skill\n'
        'model: opus\n'
        '---\n\n'
        '# Delegating Agent\n\n'
        'Uses Task tool to delegate.\n'
    )

    return bundles


@pytest.fixture
def output_dir(tmp_path):
    """Create output directory for generated files."""
    out = tmp_path / 'output' / '.opencode'
    out.mkdir(parents=True)
    return out


# =============================================================================
# parse_frontmatter tests
# =============================================================================


class TestParseFrontmatter:
    def test_basic_frontmatter(self):
        content = '---\nname: test\ndescription: A test\n---\n\n# Body\n'
        fm, body = parse_frontmatter(content)
        assert fm['name'] == 'test'
        assert fm['description'] == 'A test'
        assert '# Body' in body

    def test_no_frontmatter(self):
        content = '# Just a heading\n\nSome content.\n'
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_list_tools(self):
        content = '---\nname: test\nallowed-tools:\n  - Read\n  - Write\n  - Grep\n---\n\nBody\n'
        fm, body = parse_frontmatter(content)
        assert fm['name'] == 'test'
        assert 'Read' in fm['allowed-tools']
        assert 'Write' in fm['allowed-tools']
        assert 'Grep' in fm['allowed-tools']

    def test_inline_tools(self):
        content = '---\nname: test\ntools: Read, Write, Grep\n---\n\nBody\n'
        fm, body = parse_frontmatter(content)
        assert fm['tools'] == 'Read, Write, Grep'

    def test_multiline_description(self):
        content = '---\nname: test\ndescription: |\n  First line\n  Second line\nuser-invocable: true\n---\n\nBody\n'
        fm, body = parse_frontmatter(content)
        assert fm['name'] == 'test'
        assert 'First line' in fm['description']

    def test_boolean_values(self):
        content = '---\nname: test\nuser-invocable: true\n---\n\nBody\n'
        fm, body = parse_frontmatter(content)
        assert fm['user-invocable'] == 'true'


# =============================================================================
# Frontmatter transformation tests
# =============================================================================


class TestTransformSkillFrontmatter:
    def test_basic_transformation(self):
        fm = {'name': 'junit-core', 'description': 'JUnit 5 testing patterns'}
        result = transform_skill_frontmatter(fm, 'pm-dev-java', 'junit-core')
        assert 'name: pm-dev-java-junit-core' in result
        assert 'description: JUnit 5 testing patterns' in result
        assert 'compatibility:' in result
        assert result.startswith('---')
        assert result.endswith('---')

    def test_no_allowed_tools_in_output(self):
        """OpenCode ignores allowed-tools for skills — should not appear in output."""
        fm = {'name': 'test', 'description': 'Test', 'allowed-tools': 'Read, Write'}
        result = transform_skill_frontmatter(fm, 'bundle', 'skill')
        assert 'allowed-tools' not in result
        assert 'tools' not in result.lower().split('compatibility')[0]

    def test_multiline_description_truncated(self):
        fm = {'name': 'test', 'description': 'First line\nSecond line\nThird line'}
        result = transform_skill_frontmatter(fm, 'bundle', 'skill')
        assert 'description: First line' in result
        assert 'Second line' not in result

    def test_prefix_avoids_collision(self):
        fm1 = {'name': 'core', 'description': 'Core for A'}
        fm2 = {'name': 'core', 'description': 'Core for B'}
        r1 = transform_skill_frontmatter(fm1, 'bundle-a', 'core')
        r2 = transform_skill_frontmatter(fm2, 'bundle-b', 'core')
        assert 'name: bundle-a-core' in r1
        assert 'name: bundle-b-core' in r2


class TestTransformAgentFrontmatter:
    def test_basic_transformation(self):
        fm = {'name': 'test-agent', 'description': 'A test agent', 'tools': 'Read, Write', 'model': 'sonnet'}
        result = transform_agent_frontmatter(fm)
        assert 'description: A test agent' in result
        assert 'mode: subagent' in result
        assert f'model: {MODEL_MAP["sonnet"]}' in result

    def test_uses_permission_not_tools(self):
        """OpenCode agents use permission: object, not tools: list."""
        fm = {'name': 'agent', 'description': 'Test', 'tools': 'Read, Write, Grep'}
        result = transform_agent_frontmatter(fm)
        assert 'permission:' in result
        assert '  edit: allow' in result  # Write maps to edit permission
        assert '  read: allow' in result
        assert '  grep: allow' in result
        # Should NOT have comma-separated tools: line
        assert 'tools:' not in result

    def test_no_name_field(self):
        """OpenCode uses filename as identifier, not a name: field."""
        fm = {'name': 'test-agent', 'description': 'Test'}
        result = transform_agent_frontmatter(fm)
        assert 'name:' not in result

    def test_claude_only_tools_filtered_from_permissions(self):
        fm = {'name': 'agent', 'description': 'Test', 'tools': 'Read, Task, Skill, Write'}
        result = transform_agent_frontmatter(fm)
        assert 'task' not in result.lower()
        assert 'skill' not in result.lower()
        assert '  edit: allow' in result
        assert '  read: allow' in result

    def test_unknown_model_skipped(self):
        fm = {'name': 'agent', 'description': 'Test', 'model': 'gpt-4'}
        result = transform_agent_frontmatter(fm)
        assert 'model:' not in result


class TestTransformCommandFrontmatter:
    def test_basic_transformation(self):
        fm = {'name': 'test-cmd', 'description': 'A command', 'allowed-tools': 'Read, Write, Bash'}
        result = transform_command_frontmatter(fm)
        assert 'description: A command' in result
        assert result.startswith('---')
        assert result.endswith('---')

    def test_no_tools_field(self):
        """OpenCode commands don't have a tools: field."""
        fm = {'name': 'cmd', 'description': 'Test', 'allowed-tools': 'Read, Write'}
        result = transform_command_frontmatter(fm)
        assert 'tools:' not in result.lower()

    def test_no_name_field(self):
        """OpenCode uses filename as command name."""
        fm = {'name': 'my-cmd', 'description': 'Test'}
        result = transform_command_frontmatter(fm)
        assert 'name:' not in result


# =============================================================================
# Tool name and permission mapping tests
# =============================================================================


class TestToolNameMapping:
    def test_common_tools(self):
        assert TOOL_NAME_MAP['Read'] == 'read'
        assert TOOL_NAME_MAP['Write'] == 'write'
        assert TOOL_NAME_MAP['Edit'] == 'edit'
        assert TOOL_NAME_MAP['Glob'] == 'glob'
        assert TOOL_NAME_MAP['Grep'] == 'grep'
        assert TOOL_NAME_MAP['Bash'] == 'bash'

    def test_askuserquestion_maps_to_question(self):
        """OpenCode's equivalent of AskUserQuestion is the question tool."""
        assert TOOL_NAME_MAP['AskUserQuestion'] == 'question'

    def test_notebookedit_maps_to_edit(self):
        """NotebookEdit maps to edit permission category in OpenCode."""
        assert TOOL_NAME_MAP['NotebookEdit'] == 'edit'


class TestToolPermissionMapping:
    def test_write_maps_to_edit_permission(self):
        """OpenCode groups Write under the edit permission category."""
        assert TOOL_PERMISSION_MAP['Write'] == 'edit'
        assert TOOL_PERMISSION_MAP['Edit'] == 'edit'

    def test_read_is_separate_permission(self):
        assert TOOL_PERMISSION_MAP['Read'] == 'read'

    def test_bash_is_separate_permission(self):
        assert TOOL_PERMISSION_MAP['Bash'] == 'bash'


# =============================================================================
# Body transformation tests
# =============================================================================


class TestTransformBody:
    def test_skill_directive_annotated(self):
        body = 'Some intro.\n\nSkill: other-bundle:other-skill\n\nMore content.\n'
        result = transform_body(body, 'current-bundle')
        assert 'Skill: other-bundle:other-skill' in result
        assert '<!-- OpenCode: use skill tool to load "other-bundle-other-skill" -->' in result

    def test_skill_directive_without_bundle(self):
        body = 'Skill: local-skill\n'
        result = transform_body(body, 'my-bundle')
        assert '<!-- OpenCode: use skill tool to load "my-bundle-local-skill" -->' in result

    def test_non_directive_text_unchanged(self):
        body = 'Regular text about skills.\n\nNo directives here.\n'
        result = transform_body(body, 'bundle')
        assert result == body

    def test_multiple_directives(self):
        body = 'Skill: a:b\n\nText.\n\nSkill: c:d\n'
        result = transform_body(body, 'x')
        assert result.count('<!-- OpenCode:') == 2


# =============================================================================
# Claude-only tool detection tests
# =============================================================================


class TestAgentUsesClaudeOnlyTools:
    def test_no_tools(self):
        assert agent_uses_claude_only_tools({}) is False

    def test_safe_tools(self):
        assert agent_uses_claude_only_tools({'tools': 'Read, Write, Grep'}) is False

    def test_task_tool(self):
        assert agent_uses_claude_only_tools({'tools': 'Read, Task, Write'}) is True

    def test_skill_tool(self):
        assert agent_uses_claude_only_tools({'tools': 'Read, Skill'}) is True

    def test_both_claude_tools(self):
        assert agent_uses_claude_only_tools({'tools': 'Task, Skill'}) is True


# =============================================================================
# Full adapter integration tests
# =============================================================================


class TestOpenCodeAdapter:
    def test_adapter_name(self, adapter):
        assert adapter.name() == 'opencode'

    def test_supports_agents(self, adapter):
        assert adapter.supports_agents() is True

    def test_supports_commands(self, adapter):
        assert adapter.supports_commands() is True

    def test_generate_skills(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        # Check skill was generated with bundle prefix
        skill_md = output_dir / 'skills' / 'test-bundle-test-skill' / 'SKILL.md'
        assert skill_md.exists(), f'Expected {skill_md}'
        content = skill_md.read_text()
        assert 'name: test-bundle-test-skill' in content
        assert 'compatibility:' in content
        assert '# Test Skill' in content

    def test_generate_standards_copied(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        std_file = output_dir / 'skills' / 'test-bundle-test-skill' / 'standards' / 'test-standard.md'
        assert std_file.exists()
        assert '# Test Standard' in std_file.read_text()

    def test_generate_references_copied(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        ref_file = output_dir / 'skills' / 'test-bundle-test-skill' / 'references' / 'test-ref.md'
        assert ref_file.exists()
        assert '# Test Reference' in ref_file.read_text()

    def test_generate_scripts_copied(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        script_file = output_dir / 'skills' / 'test-bundle-test-skill' / 'scripts' / 'test_script.py'
        assert script_file.exists()
        assert 'print("hello")' in script_file.read_text()

    def test_generate_agents_exported(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        agent_md = output_dir / 'agents' / 'test-agent.md'
        assert agent_md.exists()
        content = agent_md.read_text()
        assert 'description: A test agent' in content
        assert 'mode: subagent' in content
        assert f'model: {MODEL_MAP["sonnet"]}' in content
        assert 'permission:' in content

    def test_generate_claude_only_agents_skipped(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        delegating = output_dir / 'agents' / 'delegating-agent.md'
        assert not delegating.exists(), 'Agent with Task/Skill tools should be skipped'

    def test_generate_commands_exported(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        cmd_md = output_dir / 'commands' / 'test-command.md'
        assert cmd_md.exists()
        content = cmd_md.read_text()
        assert 'description: A test command' in content
        # OpenCode commands should NOT have tools: or name: fields
        assert 'tools:' not in content.lower()

    def test_generate_opencode_json(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        config_path = output_dir.parent / 'opencode.json'
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config['$schema'] == 'https://opencode.ai/config.json'
        assert 'instructions' in config
        # Should include skills.paths pointing to generated skills
        assert 'skills' in config
        assert 'paths' in config['skills']

    def test_skill_directive_transformed(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir)

        skill_md = output_dir / 'skills' / 'test-bundle-test-skill' / 'SKILL.md'
        content = skill_md.read_text()
        assert '<!-- OpenCode: use skill tool to load "other-bundle-other-skill" -->' in content

    def test_bundle_filtering(self, adapter, marketplace_dir, output_dir):
        adapter.generate(marketplace_dir, output_dir, bundles=['test-bundle'])

        # test-bundle content should exist
        skill_md = output_dir / 'skills' / 'test-bundle-test-skill' / 'SKILL.md'
        assert skill_md.exists()

        # claude-heavy content should NOT exist (filtered out)
        delegating = output_dir / 'agents' / 'delegating-agent.md'
        assert not delegating.exists()

    def test_bundle_filtering_nonexistent(self, adapter, marketplace_dir, output_dir):
        """Filtering to a nonexistent bundle produces only opencode.json."""
        generated = adapter.generate(marketplace_dir, output_dir, bundles=['nonexistent'])
        # Only opencode.json should be generated
        assert len(generated) == 1
        assert generated[0].name == 'opencode.json'

    def test_generated_file_count(self, adapter, marketplace_dir, output_dir):
        generated = adapter.generate(marketplace_dir, output_dir)
        # Should include: SKILL.md + standard + reference + script + agent + command + opencode.json
        assert len(generated) >= 7

    def test_idempotent_generation(self, adapter, marketplace_dir, output_dir):
        """Running generate twice produces the same result."""
        gen1 = adapter.generate(marketplace_dir, output_dir)
        # Clean and regenerate
        for item in output_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        gen2 = adapter.generate(marketplace_dir, output_dir)
        assert len(gen1) == len(gen2)

    def test_bundle_path_traversal_rejected(self, adapter, marketplace_dir, output_dir):
        """Bundle names with path traversal sequences are rejected."""
        generated = adapter.generate(marketplace_dir, output_dir, bundles=['../../etc'])
        # Only opencode.json — traversal bundle was rejected
        assert len(generated) == 1
        assert generated[0].name == 'opencode.json'

    def test_bundle_with_slash_rejected(self, adapter, marketplace_dir, output_dir):
        """Bundle names containing slashes are rejected."""
        generated = adapter.generate(marketplace_dir, output_dir, bundles=['foo/bar'])
        assert len(generated) == 1

    def test_safe_rmtree_rejects_outside_output(self, adapter, tmp_path):
        """_safe_rmtree refuses to delete directories outside output_dir."""
        outside = tmp_path / 'outside'
        outside.mkdir()
        output = tmp_path / 'output'
        output.mkdir()
        with pytest.raises(ValueError, match='not within output directory'):
            adapter._safe_rmtree(outside, output)

    def test_safe_rmtree_allows_inside_output(self, adapter, tmp_path):
        """_safe_rmtree allows deletion within output_dir."""
        output = tmp_path / 'output'
        inside = output / 'subdir'
        inside.mkdir(parents=True)
        (inside / 'file.txt').write_text('test')
        adapter._safe_rmtree(inside, output)
        assert not inside.exists()


# =============================================================================
# Model mapping tests
# =============================================================================


class TestModelMapping:
    def test_known_models(self):
        assert 'opus' in MODEL_MAP
        assert 'sonnet' in MODEL_MAP
        assert 'haiku' in MODEL_MAP

    def test_model_values_follow_provider_slash_model_format(self):
        """OpenCode requires provider/model-id format."""
        for model_id in MODEL_MAP.values():
            assert '/' in model_id
            assert model_id.startswith('anthropic/')
