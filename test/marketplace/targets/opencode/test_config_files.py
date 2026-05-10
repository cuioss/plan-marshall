"""Schema validation tests for OpenCode mapping/rules JSON config files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.opencode.frontmatter import load_mapping, load_rules


@pytest.fixture()
def opencode_config_dir() -> Path:
    return Path(__file__).resolve().parents[3].parent / 'marketplace' / 'targets' / 'opencode'


# ---------------------------------------------------------------------------
# mapping.json
# ---------------------------------------------------------------------------

class TestMappingJsonSchema:
    def test_file_exists(self, opencode_config_dir: Path):
        assert (opencode_config_dir / 'mapping.json').is_file()

    def test_loads_as_object_with_required_keys(self, opencode_config_dir: Path):
        data = load_mapping(opencode_config_dir)
        assert isinstance(data, dict)
        assert 'tool_permissions' in data
        assert 'model_map' in data

    def test_tool_permissions_string_to_string(self, opencode_config_dir: Path):
        data = load_mapping(opencode_config_dir)
        for key, value in data['tool_permissions'].items():
            assert isinstance(key, str), f'tool_permissions key must be str: {key!r}'
            assert isinstance(value, str), f'tool_permissions[{key!r}] must be str'
            assert value, 'tool_permissions values must be non-empty'

    def test_model_map_object_shape(self, opencode_config_dir: Path):
        """Each model_map entry is `{id: str, supports_effort: list[str]}`."""
        data = load_mapping(opencode_config_dir)
        allowed_efforts = {'medium', 'high', 'xhigh', 'max'}
        for key, entry in data['model_map'].items():
            assert isinstance(key, str)
            assert isinstance(entry, dict), f'model_map[{key!r}] must be a dict'
            assert 'id' in entry, f'model_map[{key!r}] missing id'
            assert isinstance(entry['id'], str) and entry['id']
            assert 'supports_effort' in entry, f'model_map[{key!r}] missing supports_effort'
            assert isinstance(entry['supports_effort'], list)
            for effort in entry['supports_effort']:
                assert isinstance(effort, str)
                assert effort in allowed_efforts, f'unknown effort {effort!r} in {key}'

    def test_canonical_model_aliases_present(self, opencode_config_dir: Path):
        data = load_mapping(opencode_config_dir)
        # The three Claude aliases must each resolve to a model entry with an id.
        for alias in ('opus', 'sonnet', 'haiku'):
            assert alias in data['model_map'], f'missing alias: {alias}'
            assert data['model_map'][alias]['id'], f'{alias} entry missing id'

    def test_canonical_tools_mapped(self, opencode_config_dir: Path):
        data = load_mapping(opencode_config_dir)
        # The most-used Claude tools must always have a mapping.
        for tool in ('Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob'):
            assert tool in data['tool_permissions'], f'unmapped tool: {tool}'


# ---------------------------------------------------------------------------
# frontmatter-rules.json
# ---------------------------------------------------------------------------

class TestFrontmatterRulesSchema:
    def test_file_exists(self, opencode_config_dir: Path):
        assert (opencode_config_dir / 'frontmatter-rules.json').is_file()

    def test_loads_as_object_with_required_fields(self, opencode_config_dir: Path):
        data = load_rules(opencode_config_dir)
        assert isinstance(data, dict)
        assert 'required_fields' in data

    def test_required_fields_is_list_of_strings(self, opencode_config_dir: Path):
        data = load_rules(opencode_config_dir)
        assert isinstance(data['required_fields'], list)
        for field in data['required_fields']:
            assert isinstance(field, str)
            assert field, 'required field names must be non-empty'

    def test_optional_fields_is_list_of_strings_when_present(self, opencode_config_dir: Path):
        data = load_rules(opencode_config_dir)
        if 'optional_fields' in data:
            assert isinstance(data['optional_fields'], list)
            for field in data['optional_fields']:
                assert isinstance(field, str)

    def test_description_is_required(self, opencode_config_dir: Path):
        """All emitted artifact kinds (skill/agent/command) require ``description``."""
        data = load_rules(opencode_config_dir)
        assert 'description' in data['required_fields']


# ---------------------------------------------------------------------------
# Loader fail-fast on malformed input
# ---------------------------------------------------------------------------

class TestLoaderFailFast:
    def test_load_mapping_rejects_non_object(self, tmp_path: Path):
        (tmp_path / 'mapping.json').write_text('"a string"', encoding='utf-8')
        with pytest.raises(ValueError):
            load_mapping(tmp_path)

    def test_load_mapping_rejects_invalid_json(self, tmp_path: Path):
        (tmp_path / 'mapping.json').write_text('{not json}', encoding='utf-8')
        with pytest.raises(json.JSONDecodeError):
            load_mapping(tmp_path)

    def test_load_rules_rejects_non_object(self, tmp_path: Path):
        (tmp_path / 'frontmatter-rules.json').write_text('[1,2]', encoding='utf-8')
        with pytest.raises(ValueError):
            load_rules(tmp_path)

    def test_load_rules_rejects_invalid_json(self, tmp_path: Path):
        (tmp_path / 'frontmatter-rules.json').write_text('not-json', encoding='utf-8')
        with pytest.raises(json.JSONDecodeError):
            load_rules(tmp_path)
