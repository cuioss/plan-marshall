"""Per-rule unit tests for OpenCode frontmatter transforms."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketplace.targets.opencode.frontmatter import (
    OPENCODE_MODEL_PREFIX,
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
def opencode_config_dir() -> Path:
    """Path to the canonical OpenCode mapping/rules config directory."""
    return Path(__file__).resolve().parents[3].parent / 'marketplace' / 'targets' / 'opencode'


@pytest.fixture()
def mapping(opencode_config_dir: Path) -> dict[str, dict[str, str]]:
    return load_mapping(opencode_config_dir)


@pytest.fixture()
def rules(opencode_config_dir: Path) -> dict[str, list[str]]:
    return load_rules(opencode_config_dir)


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_and_full_body(self):
        fm, body = parse_frontmatter('# heading\nplain body\n')
        assert fm == {}
        assert body == '# heading\nplain body\n'

    def test_unterminated_frontmatter_returns_empty(self):
        fm, body = parse_frontmatter('---\nname: x\nno closing fence\n')
        assert fm == {}

    def test_simple_keys_parsed(self):
        content = '---\nname: foo\ndescription: a desc\n---\nbody\n'
        fm, body = parse_frontmatter(content)
        assert fm['name'] == 'foo'
        assert fm['description'] == 'a desc'
        assert body == 'body\n'

    def test_list_value_flattened_to_csv(self):
        content = '---\ntools:\n  - Read\n  - Write\n  - Edit\n---\nbody\n'
        fm, _ = parse_frontmatter(content)
        assert fm['tools'] == 'Read, Write, Edit'

    def test_inline_csv_passed_through(self):
        content = '---\ntools: Read, Write\n---\nbody\n'
        fm, _ = parse_frontmatter(content)
        assert fm['tools'] == 'Read, Write'

    def test_multiline_block_aggregated(self):
        content = '---\ndescription: |\n  line one\n  line two\nname: x\n---\nbody\n'
        fm, _ = parse_frontmatter(content)
        assert 'line one' in fm['description']
        assert 'line two' in fm['description']
        assert fm['name'] == 'x'


# ---------------------------------------------------------------------------
# tool → permission mapping
# ---------------------------------------------------------------------------

class TestToolPermissionMapping:
    def test_known_tools_map_to_permissions(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {
            'description': 'agent',
            'tools': 'Read, Write, Bash',
        }
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'read: allow' in result
        assert 'edit: allow' in result  # Write maps to edit
        assert 'bash: allow' in result

    def test_duplicate_permissions_deduplicated(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {
            'description': 'agent',
            # Write and Edit both map to 'edit'
            'tools': 'Write, Edit',
        }
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        # 'edit: allow' appears exactly once
        assert result.count('edit: allow') == 1

    def test_unmapped_tool_raises(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {'description': 'agent', 'tools': 'Read, BogusTool'}
        with pytest.raises(UnmappedToolError):
            transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')

    def test_no_tools_field_omits_permission_block(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {'description': 'agent'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'permission:' not in result


# ---------------------------------------------------------------------------
# model alias resolution
# ---------------------------------------------------------------------------

class TestModelAliasResolution:
    def test_known_alias_resolves_to_prefixed_id(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {'description': 'agent', 'model': 'sonnet'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        sonnet_id = mapping['model_map']['sonnet']['id']
        assert f'model: {OPENCODE_MODEL_PREFIX}{sonnet_id}' in result

    def test_unknown_alias_passes_through(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {'description': 'agent', 'model': 'anthropic/custom-model'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'model: anthropic/custom-model' in result

    def test_no_model_field_omits_model_line(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        fm = {'description': 'agent'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'model:' not in result


# ---------------------------------------------------------------------------
# required-field validation
# ---------------------------------------------------------------------------

class TestRequiredFieldValidation:
    def test_skill_missing_description_raises(self, rules: dict[str, list[str]]):
        with pytest.raises(UnmappedFrontmatterError):
            transform_skill_frontmatter(
                {'name': 'x'}, 'demo', 'x', rules, source_label='skills/x/SKILL.md'
            )

    def test_agent_missing_description_raises(
        self, mapping: dict[str, dict[str, str]], rules: dict[str, list[str]]
    ):
        with pytest.raises(UnmappedFrontmatterError):
            transform_agent_frontmatter({}, mapping, rules, source_label='agents/x.md')

    def test_command_missing_description_raises(self, rules: dict[str, list[str]]):
        with pytest.raises(UnmappedFrontmatterError):
            transform_command_frontmatter({}, rules, source_label='commands/x.md')

    def test_skill_present_description_emits_compatibility_marker(
        self, rules: dict[str, list[str]]
    ):
        result = transform_skill_frontmatter(
            {'description': 'a skill'},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert 'name: demo-x' in result
        assert 'description: a skill' in result
        assert 'compatibility:' in result


# ---------------------------------------------------------------------------
# load_mapping / load_rules error paths
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_missing_mapping_raises_filenotfound(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_mapping(tmp_path)

    def test_missing_rules_raises_filenotfound(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_rules(tmp_path)

    def test_malformed_mapping_rejected(self, tmp_path: Path):
        (tmp_path / 'mapping.json').write_text('[]', encoding='utf-8')
        with pytest.raises(ValueError):
            load_mapping(tmp_path)

    def test_mapping_missing_required_keys_rejected(self, tmp_path: Path):
        (tmp_path / 'mapping.json').write_text('{"tool_permissions": {}}', encoding='utf-8')
        with pytest.raises(ValueError):
            load_mapping(tmp_path)
