# SPDX-License-Identifier: FSL-1.1-ALv2
"""Schema validation tests for Antigravity mapping/rules JSON config files."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.frontmatter import load_mapping, load_rules


@pytest.fixture()
def antigravity_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity'


class TestMappingJsonSchema:
    def test_file_exists(self, antigravity_config_dir: Path):
        assert (antigravity_config_dir / 'mapping.json').is_file()

    def test_loads_as_object_with_required_keys(self, antigravity_config_dir: Path):
        data = load_mapping(antigravity_config_dir)
        assert isinstance(data, dict)
        assert 'tool_permissions' in data
        assert 'model_map' in data

    def test_tool_permissions_string_to_optional_string(self, antigravity_config_dir: Path):
        data = load_mapping(antigravity_config_dir)
        for key, value in data['tool_permissions'].items():
            assert isinstance(key, str), f'tool_permissions key must be str: {key!r}'
            if value is None:
                continue
            assert isinstance(value, str), f'tool_permissions[{key!r}] must be str or None'
            assert value, 'non-null tool_permissions values must be non-empty'

    def test_key_primitives_mapped(self, antigravity_config_dir: Path):
        data = load_mapping(antigravity_config_dir)
        perms = data['tool_permissions']
        assert perms.get('Bash') == 'run_command'
        assert perms.get('Read') == 'view_file'
        assert perms.get('Write') == 'write_to_file'
        assert perms.get('Edit') == 'replace_file_content'
        assert perms.get('Glob') == 'find_by_name'
        assert perms.get('Grep') == 'grep_search'
        assert perms.get('AskUserQuestion') == 'ask_question'
        assert perms.get('Task') == 'invoke_subagent'

    def test_notebook_edit_is_target_absent(self, antigravity_config_dir: Path):
        data = load_mapping(antigravity_config_dir)
        assert 'NotebookEdit' in data['tool_permissions']
        assert data['tool_permissions']['NotebookEdit'] is None

    def test_model_map_entries(self, antigravity_config_dir: Path):
        data = load_mapping(antigravity_config_dir)
        mmap = data['model_map']
        for alias in ('opus', 'sonnet', 'haiku', 'fable'):
            assert alias in mmap
            assert 'id' in mmap[alias]
            assert isinstance(mmap[alias]['id'], str)


class TestFrontmatterRulesJsonSchema:
    def test_file_exists(self, antigravity_config_dir: Path):
        assert (antigravity_config_dir / 'frontmatter-rules.json').is_file()

    def test_loads_as_object_with_required_fields(self, antigravity_config_dir: Path):
        rules = load_rules(antigravity_config_dir)
        assert isinstance(rules, dict)
        assert 'required_fields' in rules
        req = rules['required_fields']
        assert isinstance(req, list)
        assert 'description' in req
