# SPDX-License-Identifier: FSL-1.1-ALv2
"""Structural-compliance tests for the default:finalize-step-print-phase-breakdown
built-in finalize step.

The step is a markdown standards document under
``marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/`` (no
Python entry point — same shape as ``default:push``,
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
    return str(STANDARDS_PATH.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def frontmatter(standards_text: str) -> dict[str, str]:
    return _parse_frontmatter(standards_text)


class TestStandardsFrontmatter:
    """Frontmatter contract for built-in finalize steps (default:* shape)."""

    def test_standards_file_exists(self):
        assert STANDARDS_PATH.is_file()

    def test_name_uses_default_prefix(self, frontmatter: dict[str, str]):
        # Built-in steps live under standards/ and their `name` carries the
        # `default:` prefix verbatim — same as push, record-metrics,
        # archive-plan, etc.
        assert frontmatter['name'] == 'default:finalize-step-print-phase-breakdown'

    def test_description_present(self, frontmatter: dict[str, str]):
        description = frontmatter.get('description', '')
        assert description, 'frontmatter description is required'
        assert len(description) >= 30, f'description too short: {description!r}'

    def test_order_is_999(self, frontmatter: dict[str, str]):
        # 999 slots after record-metrics (998, which writes metrics.md) and
        # before archive-plan (1000). record-metrics is the last token-accounting
        # step, so print-phase-breakdown — which reads the generated metrics.md —
        # must resolve immediately above it in the finalize tail.
        assert frontmatter['order'] == '999'


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


class TestCollapsedProducerPattern:
    """The standards doc collapses the producer pattern from 3 steps to 1.

    Pre-collapse shape: capture stdout from `manage-metrics print-phase-breakdown`,
    Write the captured content to `.plan/temp/...`, then `manage-files write
    --content-file ...`. Post-collapse shape: one direct `manage-metrics
    print-phase-breakdown` invocation that writes the artifact file itself and
    returns the bytes_written count in TOON.
    """

    def test_no_content_file_flag(self, standards_text: str):
        # The collapsed shape no longer stages content to .plan/temp/ and then
        # invokes `manage-files write --content-file`.
        assert '--content-file' not in standards_text, (
            'collapsed producer must not reference --content-file (was used by '
            'the 3-step staging pattern)'
        )

    def test_no_plan_temp_staging(self, standards_text: str):
        # No `.plan/temp/` staging language remains.
        assert '.plan/temp/' not in standards_text, (
            'collapsed producer must not reference .plan/temp/ staging path'
        )

    def test_no_manage_files_write_step(self, standards_text: str):
        # `manage-files write` should no longer appear as a producer step. We
        # still allow the bundle name to surface in cross-references, so check
        # for the verb-level invocation pattern.
        assert 'manage-files write' not in standards_text, (
            "collapsed producer must not invoke 'manage-files write' (the "
            'producer writes the artifact directly)'
        )

    def test_single_producer_bash_block(self, standards_text: str):
        # Exactly one Bash block invokes `manage-metrics print-phase-breakdown`.
        # Find all fenced bash blocks and count matches.
        bash_blocks = re.findall(r'```bash\n(.*?)```', standards_text, re.DOTALL)
        producer_blocks = [
            block for block in bash_blocks
            if 'manage-metrics:manage-metrics print-phase-breakdown' in block
        ]
        assert len(producer_blocks) == 1, (
            f'expected exactly one producer Bash block invoking '
            f'manage-metrics print-phase-breakdown, found {len(producer_blocks)}'
        )

    def test_documents_bytes_written_return_field(self, standards_text: str):
        # The collapsed pattern consumes `bytes_written` from the script's
        # returned TOON envelope (replaces the prior `manage-files write` return).
        assert 'bytes_written' in standards_text, (
            'collapsed producer must document the bytes_written field from '
            'the print-phase-breakdown TOON envelope'
        )


class TestDispatchTableRegistration:
    """The phase-6-finalize SKILL.md dispatch table routes the new step."""

    def test_dispatch_table_lists_standards_path(self):
        text = PHASE_6_SKILL_PATH.read_text(encoding='utf-8')
        # Dispatch table maps default:{name} -> standards/{name}.md.
        assert 'default:finalize-step-print-phase-breakdown' in text
        assert 'standards/finalize-step-print-phase-breakdown.md' in text
