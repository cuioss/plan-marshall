# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-rule unit tests for OpenCode frontmatter transforms."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import PROJECT_ROOT, load_script_module
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

# The closed `mode` vocabulary, read from the rule that OWNS it rather than
# restated here. The plugin-doctor analyzer that fails a skill with no `mode`
# is the same component that defines which values are legal, so it is the
# declaring source for that set; duplicating the four literals in this file
# would let a fifth mode be added to the validator while these passthrough
# cases kept asserting the old four — a green test covering a vocabulary that
# no longer exists.
_skill_mode_analyzer = load_script_module('pm-plugin-development', 'plugin-doctor', '_analyze_skill_mode.py')
VALID_MODES: frozenset[str] = _skill_mode_analyzer._VALID_MODES


@pytest.fixture()
def opencode_config_dir() -> Path:
    """Path to the canonical OpenCode mapping/rules config directory."""
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'opencode'


@pytest.fixture()
def mapping(opencode_config_dir: Path) -> dict[str, dict]:
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

    def test_value_containing_triple_dash_does_not_truncate(self):
        """A value carrying ``---`` must not end the block early.

        The closing fence is a newline-delimited ``---`` line, not a raw
        substring; a raw-substring search would stop at the ``---`` inside the
        ``description`` value and silently drop every later field.
        """
        content = '---\nname: foo\ndescription: before --- after\ntools: Read, Write\n---\nbody\n'
        fm, body = parse_frontmatter(content)
        assert fm['name'] == 'foo'
        assert fm['description'] == 'before --- after'
        assert fm['tools'] == 'Read, Write'  # dropped by a raw-substring fence
        assert body == 'body\n'

    def test_closing_fence_without_trailing_newline_tolerated(self):
        """A closing fence at end-of-file with no trailing newline still parses."""
        fm, body = parse_frontmatter('---\nname: x\ndescription: d\n---')
        assert fm['name'] == 'x'
        assert fm['description'] == 'd'
        assert body == ''


# ---------------------------------------------------------------------------
# tool → permission mapping
# ---------------------------------------------------------------------------


class TestToolPermissionMapping:
    def test_known_tools_map_to_permissions(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {
            'description': 'agent',
            'tools': 'Read, Write, Bash',
        }
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'read: allow' in result
        assert 'edit: allow' in result  # Write maps to edit
        assert 'bash: allow' in result

    def test_duplicate_permissions_deduplicated(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {
            'description': 'agent',
            # Write and Edit both map to 'edit'
            'tools': 'Write, Edit',
        }
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        # 'edit: allow' appears exactly once
        assert result.count('edit: allow') == 1

    def test_unmapped_tool_raises(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent', 'tools': 'Read, BogusTool'}
        with pytest.raises(UnmappedToolError):
            transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')

    def test_no_tools_field_omits_permission_block(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'permission:' not in result


class TestTargetAbsentToolDisposition:
    """A `tool_permissions` key present with `null` is the target-absent sentinel.

    The Claude tool exists but has no OpenCode analog, so the transform emits no
    permission entry for it and does NOT raise. The fail-closed guard is narrowed
    to a *missing key*, not removed.
    """

    def test_target_absent_tool_transforms_without_raising(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent', 'tools': 'Monitor'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'description: agent' in result

    def test_target_absent_tool_emits_no_permission_line(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent', 'tools': 'Monitor'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'permission:' not in result
        assert 'Monitor' not in result

    def test_target_absent_tool_alongside_mapped_tools_emits_only_mapped(
        self, mapping: dict[str, dict], rules: dict[str, list[str]]
    ):
        fm = {'description': 'agent', 'tools': 'Read, Monitor, Bash'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'read: allow' in result
        assert 'bash: allow' in result
        # Exactly the two mapped permissions — the sentinel contributes none.
        assert result.count(': allow') == 2

    def test_genuinely_unknown_tool_still_raises(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        """The fail-closed guard survives: a MISSING key still raises."""
        fm = {'description': 'agent', 'tools': 'Monitor, TotallyUnknownTool'}
        with pytest.raises(UnmappedToolError, match='TotallyUnknownTool'):
            transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')


# ---------------------------------------------------------------------------
# model alias resolution
# ---------------------------------------------------------------------------


class TestModelAliasResolution:
    def test_known_alias_resolves_to_prefixed_id(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent', 'model': 'sonnet'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        sonnet_id = mapping['model_map']['sonnet']['id']
        assert f'model: {OPENCODE_MODEL_PREFIX}{sonnet_id}' in result

    def test_unknown_alias_passes_through(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent', 'model': 'anthropic/custom-model'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'model: anthropic/custom-model' in result

    def test_qualified_provider_string_passes_through(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        """A provider-qualified string passes through unchanged (provider kind)."""
        fm = {'description': 'agent', 'model': 'zen/route-r'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'model: zen/route-r' in result

    def test_local_model_string_passes_through(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        """A local model string passes through unchanged (local kind)."""
        fm = {'description': 'agent', 'model': 'local-model-a'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'model: local-model-a' in result

    def test_no_model_field_omits_model_line(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        fm = {'description': 'agent'}
        result = transform_agent_frontmatter(fm, mapping, rules, source_label='agents/x.md')
        assert 'model:' not in result


# ---------------------------------------------------------------------------
# required-field validation
# ---------------------------------------------------------------------------


class TestRequiredFieldValidation:
    def test_skill_missing_description_raises(self, rules: dict[str, list[str]]):
        with pytest.raises(UnmappedFrontmatterError):
            transform_skill_frontmatter({'name': 'x'}, 'demo', 'x', rules, source_label='skills/x/SKILL.md')

    def test_agent_missing_description_raises(self, mapping: dict[str, dict], rules: dict[str, list[str]]):
        with pytest.raises(UnmappedFrontmatterError):
            transform_agent_frontmatter({}, mapping, rules, source_label='agents/x.md')

    def test_command_missing_description_raises(self, rules: dict[str, list[str]]):
        with pytest.raises(UnmappedFrontmatterError):
            transform_command_frontmatter({}, rules, source_label='commands/x.md')

    def test_skill_present_description_emits_compatibility_marker(self, rules: dict[str, list[str]]):
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
# Skill `mode` passthrough — the execution archetype
# ---------------------------------------------------------------------------


class TestSkillModePassthrough:
    """``mode`` names a skill's execution archetype and must survive emission.

    ``persona-plan-marshall-agent`` treats ``mode`` as *the* source of truth for
    how a skill is consumed, and the unconditionally-active ``skill-missing-mode``
    plugin-doctor rule fails a skill that declares none. An emitter that drops the
    field therefore makes every emitted skill unclassifiable — and reds any
    whole-tree gate that reaches the deployed cache. ``mode`` is already listed in
    ``frontmatter-rules.json``'s ``optional_fields``, so this is the documented
    passthrough, not a new capability.
    """

    def test_mode_is_emitted_verbatim(self, rules: dict[str, list[str]]):
        result = transform_skill_frontmatter(
            {'description': 'a skill', 'mode': 'script-executor'},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert 'mode: script-executor' in result

    @pytest.mark.parametrize('mode', sorted(VALID_MODES))
    def test_every_valid_mode_survives(self, mode: str, rules: dict[str, list[str]]):
        """The whole closed vocabulary, taken from the validator that owns it.

        A transformer that hard-coded a single value would pass a one-case
        test and still corrupt the rest, so every legal mode is asserted. The
        set is read from ``_VALID_MODES`` rather than restated, so adding a
        fifth mode to the rule extends these cases instead of silently
        leaving them covering a vocabulary that no longer exists.
        """
        result = transform_skill_frontmatter(
            {'description': 'a skill', 'mode': mode},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert f'mode: {mode}' in result

    def test_valid_modes_set_is_not_empty(self):
        """Guard on the guard.

        A parametrized suite over an empty set collects nothing and reports
        green, so the derived set is asserted non-empty — the same
        confident-empty defect the coverage rules elsewhere in this repo
        refuse.
        """
        assert VALID_MODES, 'the derived mode vocabulary must not be empty'

    def test_absent_mode_emits_no_mode_key(self, rules: dict[str, list[str]]):
        """No invented default.

        Defaulting a missing ``mode`` would fabricate an archetype the author
        never chose, and would silence the ``skill-missing-mode`` rule on the
        very source-level gap that rule exists to report.
        """
        result = transform_skill_frontmatter(
            {'description': 'a skill'},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert 'mode:' not in result

    @pytest.mark.parametrize('declared', ['', '   '])
    def test_blank_mode_is_treated_as_absent(self, declared: str, rules: dict[str, list[str]]):
        """An empty or whitespace-only value declares nothing.

        Emitting ``mode:`` with no value would produce a key that satisfies a
        naive substring check while classifying nothing.
        """
        result = transform_skill_frontmatter(
            {'description': 'a skill', 'mode': declared},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert 'mode:' not in result

    def test_unrecognised_mode_is_not_coerced(self, rules: dict[str, list[str]]):
        """An invalid value stays invalid so the doctor rule can surface it.

        Normalising it into a legal-looking token would make the emitted skill
        claim an archetype its author never wrote.
        """
        result = transform_skill_frontmatter(
            {'description': 'a skill', 'mode': 'not-a-real-mode'},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert 'mode: not-a-real-mode' in result
        assert 'mode: workflow' not in result

    def test_mode_is_stripped(self, rules: dict[str, list[str]]):
        """Surrounding whitespace is normalised away, the token is not."""
        result = transform_skill_frontmatter(
            {'description': 'a skill', 'mode': '  workflow  '},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        assert 'mode: workflow' in result
        assert 'mode:   workflow' not in result

    def test_mode_lives_inside_the_frontmatter_block(self, rules: dict[str, list[str]]):
        """The key must be between the fences, not appended past the closing one.

        A ``mode:`` line after the closing ``---`` is body text, so the emitted
        skill would parse as declaring no archetype at all — the exact defect
        this passthrough closes, reintroduced by a formatting slip.
        """
        result = transform_skill_frontmatter(
            {'description': 'a skill', 'mode': 'workflow'},
            'demo',
            'x',
            rules,
            source_label='skills/x/SKILL.md',
        )
        block = result.split('---')[1]
        assert 'mode: workflow' in block
        assert result.count('---') == 2


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
