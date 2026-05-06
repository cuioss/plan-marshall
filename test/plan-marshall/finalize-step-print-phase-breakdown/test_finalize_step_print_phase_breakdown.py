"""Structural-compliance tests for the finalize-step-print-phase-breakdown skill.

The skill is a markdown SKILL.md (no Python entry point). These tests pin the
contract that phase-6-finalize and the output-template renderer rely on:

1. SKILL.md exists at the expected marketplace location.
2. Frontmatter declares ``user-invocable: false`` and ``allowed-tools: Bash``.
3. ``order: 995`` slots between ``record-metrics`` (990) and ``archive-plan`` (1000).
4. SKILL body documents the producer side of the cross-deliverable contract:
   it must reference ``work/phase-breakdown-output.txt`` (the artifact path the
   renderer reads) and ``manage-metrics print-phase-breakdown`` (the data
   source).
5. Frontmatter description is non-empty.
"""

# ruff: noqa: I001
from __future__ import annotations

import re

import pytest

from conftest import MARKETPLACE_ROOT


SKILL_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'finalize-step-print-phase-breakdown'
    / 'SKILL.md'
)
ARTIFACT_PATH = 'work/phase-breakdown-output.txt'


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the YAML-ish frontmatter block at the top of a SKILL.md file."""
    if not text.startswith('---\n'):
        raise ValueError('SKILL.md must start with frontmatter')
    end = text.find('\n---\n', 4)
    if end == -1:
        raise ValueError('frontmatter delimiter not closed')
    block = text[4:end]
    metadata: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or ':' not in line:
            continue
        key, _, value = line.partition(':')
        metadata[key.strip()] = value.strip()
    return metadata


@pytest.fixture(scope='module')
def skill_text() -> str:
    assert SKILL_PATH.is_file(), f'expected SKILL.md at {SKILL_PATH}'
    return SKILL_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def frontmatter(skill_text: str) -> dict[str, str]:
    return _parse_frontmatter(skill_text)


class TestSkillFrontmatter:
    """Frontmatter contract for finalize-step skills."""

    def test_skill_file_exists(self):
        assert SKILL_PATH.is_file()

    def test_name_matches_directory(self, frontmatter: dict[str, str]):
        assert frontmatter['name'] == 'finalize-step-print-phase-breakdown'

    def test_description_present(self, frontmatter: dict[str, str]):
        description = frontmatter.get('description', '')
        assert description, 'frontmatter description is required'
        assert len(description) >= 30, f'description too short: {description!r}'

    def test_user_invocable_false(self, frontmatter: dict[str, str]):
        assert frontmatter['user-invocable'] == 'false'

    def test_allowed_tools_includes_bash(self, frontmatter: dict[str, str]):
        # Frontmatter value is a comma-separated list or a single value.
        tools = [t.strip() for t in frontmatter['allowed-tools'].split(',')]
        assert 'Bash' in tools, f'allowed-tools must include Bash, got {tools!r}'

    def test_order_is_995(self, frontmatter: dict[str, str]):
        # 995 slots between record-metrics (990) and archive-plan (1000).
        assert frontmatter['order'] == '995'


class TestSkillBodyContract:
    """The skill body documents the producer side of the contract."""

    def test_references_breakdown_artifact_path(self, skill_text: str):
        # Cross-deliverable contract: producer writes the same path the
        # renderer (consumer) reads in output-template.md snapshot procedure.
        assert ARTIFACT_PATH in skill_text, (
            f'SKILL.md must reference the artifact path {ARTIFACT_PATH!r}'
        )

    def test_references_print_phase_breakdown_subcommand(self, skill_text: str):
        # Producer's data source — the manage-metrics subcommand that
        # extracts the section from metrics.md.
        assert 'print-phase-breakdown' in skill_text
        assert 'manage_metrics' in skill_text or 'manage-metrics' in skill_text

    def test_documents_mark_step_done_handshake(self, skill_text: str):
        # Finalize steps must record their outcome via mark-step-done so the
        # phase-handshake invariants stay satisfied.
        assert 'mark-step-done' in skill_text
        assert 'finalize-step-print-phase-breakdown' in skill_text

    def test_documents_error_handling_section(self, skill_text: str):
        # Finalize must not block on presentation-only failures — error
        # handling section must exist.
        assert re.search(r'(?im)^## Error Handling', skill_text), (
            'expected an Error Handling section'
        )

    def test_documents_ordering_constraint(self, skill_text: str):
        # The body explicitly notes the ordering constraint relative to
        # record-metrics and archive-plan.
        assert 'record-metrics' in skill_text
        assert 'archive-plan' in skill_text


class TestRegistration:
    """The new skill is registered in plan-marshall's plugin.json."""

    def test_skill_registered_in_plugin_json(self):
        plugin_json_path = (
            MARKETPLACE_ROOT
            / 'plan-marshall'
            / '.claude-plugin'
            / 'plugin.json'
        )
        assert plugin_json_path.is_file()
        text = plugin_json_path.read_text(encoding='utf-8')
        assert './skills/finalize-step-print-phase-breakdown' in text, (
            'plan-marshall plugin.json must register the new skill'
        )
