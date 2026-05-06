"""Structural-compliance tests for the default:finalize-step-print-phase-breakdown
built-in finalize step.

The step is a markdown standards document under
``marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/`` (no
Python entry point — same shape as ``default:commit-push``,
``default:record-metrics``, ``default:archive-plan``). These tests pin the
contract that the phase-6-finalize dispatcher and the output-template
renderer rely on:

1. Standards file exists at the expected built-in location.
2. Frontmatter declares ``name: default:finalize-step-print-phase-breakdown``
   and ``order: 995`` (slots between record-metrics 990 and archive-plan 1000).
3. Body documents the producer side of the cross-deliverable contract:
   it must reference ``work/phase-breakdown-output.txt`` (the artifact path
   the renderer reads) and ``manage-metrics print-phase-breakdown`` (the
   data source).
4. Frontmatter description is non-empty.
5. Dispatch table in phase-6-finalize/SKILL.md routes the step to this
   standards document.
"""

# ruff: noqa: I001
from __future__ import annotations

import re

import pytest

from conftest import MARKETPLACE_ROOT


STANDARDS_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'finalize-step-print-phase-breakdown.md'
)
PHASE_6_SKILL_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'SKILL.md'
)
ARTIFACT_PATH = 'work/phase-breakdown-output.txt'


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the YAML-ish frontmatter block at the top of a markdown file."""
    if not text.startswith('---\n'):
        raise ValueError('document must start with frontmatter')
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
def standards_text() -> str:
    assert STANDARDS_PATH.is_file(), f'expected standards file at {STANDARDS_PATH}'
    return STANDARDS_PATH.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def frontmatter(standards_text: str) -> dict[str, str]:
    return _parse_frontmatter(standards_text)


class TestStandardsFrontmatter:
    """Frontmatter contract for built-in finalize steps (default:* shape)."""

    def test_standards_file_exists(self):
        assert STANDARDS_PATH.is_file()

    def test_name_uses_default_prefix(self, frontmatter: dict[str, str]):
        # Built-in steps live under standards/ and their `name` carries the
        # `default:` prefix verbatim — same as commit-push, record-metrics,
        # archive-plan, etc.
        assert frontmatter['name'] == 'default:finalize-step-print-phase-breakdown'

    def test_description_present(self, frontmatter: dict[str, str]):
        description = frontmatter.get('description', '')
        assert description, 'frontmatter description is required'
        assert len(description) >= 30, f'description too short: {description!r}'

    def test_order_is_995(self, frontmatter: dict[str, str]):
        # 995 slots between record-metrics (990) and archive-plan (1000).
        assert frontmatter['order'] == '995'


class TestStandardsBodyContract:
    """The standards body documents the producer side of the contract."""

    def test_references_breakdown_artifact_path(self, standards_text: str):
        # Cross-deliverable contract: producer writes the same path the
        # renderer (consumer) reads in output-template.md snapshot procedure.
        assert ARTIFACT_PATH in standards_text, (
            f'standards must reference the artifact path {ARTIFACT_PATH!r}'
        )

    def test_references_print_phase_breakdown_subcommand(self, standards_text: str):
        # Producer's data source — the manage-metrics subcommand that
        # extracts the section from metrics.md.
        assert 'print-phase-breakdown' in standards_text
        assert 'manage_metrics' in standards_text or 'manage-metrics' in standards_text

    def test_documents_mark_step_done_handshake(self, standards_text: str):
        # Finalize steps must record their outcome via mark-step-done so the
        # phase-handshake invariants stay satisfied.
        assert 'mark-step-done' in standards_text
        assert 'finalize-step-print-phase-breakdown' in standards_text

    def test_documents_error_handling_section(self, standards_text: str):
        # Finalize must not block on presentation-only failures — error
        # handling section must exist.
        assert re.search(r'(?im)^## Error Handling', standards_text), (
            'expected an Error Handling section'
        )

    def test_documents_ordering_constraint(self, standards_text: str):
        # The body explicitly notes the ordering constraint relative to
        # record-metrics and archive-plan.
        assert 'record-metrics' in standards_text
        assert 'archive-plan' in standards_text


class TestDispatchTableRegistration:
    """The phase-6-finalize SKILL.md dispatch table routes the new step."""

    def test_dispatch_table_lists_standards_path(self):
        text = PHASE_6_SKILL_PATH.read_text(encoding='utf-8')
        # Dispatch table maps default:{name} -> standards/{name}.md.
        assert 'default:finalize-step-print-phase-breakdown' in text
        assert 'standards/finalize-step-print-phase-breakdown.md' in text
