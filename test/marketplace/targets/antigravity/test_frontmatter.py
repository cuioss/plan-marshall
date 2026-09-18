# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for Antigravity frontmatter transforms."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.frontmatter import (
    UnmappedFrontmatterError,
    UnmappedToolError,
    load_mapping,
    load_rules,
    parse_frontmatter,
    transform_agent_frontmatter,
    transform_command_frontmatter,
    transform_skill_frontmatter,
)


@pytest.fixture()
def antigravity_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity'


@pytest.fixture()
def mapping(antigravity_config_dir: Path) -> dict[str, dict]:
    return load_mapping(antigravity_config_dir)


@pytest.fixture()
def rules(antigravity_config_dir: Path) -> dict[str, list[str]]:
    return load_rules(antigravity_config_dir)


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_and_body(self):
        fm, body = parse_frontmatter('# Hello\nWorld')
        assert fm == {}
        assert body == '# Hello\nWorld'

    def test_unterminated_frontmatter(self):
        fm, body = parse_frontmatter('---\nname: foo\n')
        assert fm == {}

    def test_parses_simple_frontmatter(self):
        content = '---\nname: foo\ndescription: bar\n---\nBody'
        fm, body = parse_frontmatter(content)
        assert fm['name'] == 'foo'
        assert fm['description'] == 'bar'
        assert body == 'Body'


class TestTransformSkillFrontmatter:
    def test_requires_name_and_description(self, rules: dict):
        with pytest.raises(UnmappedFrontmatterError):
            transform_skill_frontmatter({}, 'bundle', 'skill', rules)

    def test_transforms_skill_successfully(self, rules: dict):
        fm = {'name': 'test-skill', 'description': 'A test skill'}
        res = transform_skill_frontmatter(fm, 'test-bundle', 'test-skill', rules)
        assert 'name: test-bundle-test-skill' in res
        assert 'description: A test skill' in res
        assert 'compatibility:' in res

    def test_description_with_special_chars_is_quoted(self, rules: dict):
        fm = {'name': 'test-skill', 'description': 'Do something: important "quoted" task'}
        res = transform_skill_frontmatter(fm, 'test-bundle', 'test-skill', rules)
        assert 'description: "Do something: important \\"quoted\\" task"' in res


class TestTransformAgentFrontmatter:
    def test_requires_description(self, mapping: dict, rules: dict):
        with pytest.raises(UnmappedFrontmatterError):
            transform_agent_frontmatter({}, mapping, rules, source_label='agent/test')

    def test_transforms_tools_and_model(self, mapping: dict, rules: dict):
        fm = {
            'name': 'test-agent',
            'description': 'An agent',
            'model': 'sonnet',
            'tools': 'Read, Write, Bash',
        }
        res = transform_agent_frontmatter(fm, mapping, rules, source_label='agent/test')
        assert 'mode: subagent' in res
        assert 'model: pro' in res
        assert 'run_command' in res
        assert 'view_file' in res
        assert 'write_to_file' in res

    def test_unmapped_tool_raises_error(self, mapping: dict, rules: dict):
        fm = {
            'name': 'test-agent',
            'description': 'An agent',
            'tools': 'UnknownToolXYZ',
        }
        with pytest.raises(UnmappedToolError):
            transform_agent_frontmatter(fm, mapping, rules, source_label='agent/test')

    def test_target_absent_tool_omitted(self, mapping: dict, rules: dict):
        fm = {
            'name': 'test-agent',
            'description': 'An agent',
            'tools': 'Read, NotebookEdit',
        }
        res = transform_agent_frontmatter(fm, mapping, rules, source_label='agent/test')
        assert 'view_file' in res
        assert 'NotebookEdit' not in res


class TestTransformCommandFrontmatter:
    def test_transforms_command(self, rules: dict):
        fm = {'name': 'my-cmd', 'description': 'Run something'}
        res = transform_command_frontmatter(fm, rules, source_label='command/test')
        assert 'description: Run something' in res
