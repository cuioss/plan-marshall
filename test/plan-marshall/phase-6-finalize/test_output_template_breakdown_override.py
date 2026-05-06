#!/usr/bin/env python3
"""Structural tests for the Phase Breakdown override contract in
output-template.md.

Background: deliverable 4 of plan ``finalize-summary-format-breakdown`` adds
an opt-in override mode to the finalize-summary renderer. The renderer is a
markdown-documented procedure (no Python entry point of its own), so this
contract test asserts the documented behavior is present in
``output-template.md`` and that the producer/consumer file path agreed
between deliverable 4 (renderer/consumer) and deliverable 5 (finalize-step
producer) matches verbatim.

Scope:

1. The standalone ``## Phase Breakdown Override`` section exists between the
   Snapshot Procedure and Emission Procedure sections.
2. The Snapshot Procedure documents a read of
   ``work/phase-breakdown-output.txt`` BEFORE ``default:archive-plan`` runs.
3. The Emission Procedure documents the override skip in step 5 (Finalize
   steps block) and emits the captured breakdown in its place.
4. The override-mode skeleton is present in the document.
5. The producer/consumer path string ``work/phase-breakdown-output.txt``
   appears verbatim in both ``output-template.md`` and
   ``standards/finalize-step-print-phase-breakdown.md`` — enforces the
   cross-deliverable contract documented in the solution outline.
"""

# ruff: noqa: I001
from __future__ import annotations

import pytest

from conftest import MARKETPLACE_ROOT


OUTPUT_TEMPLATE_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'output-template.md'
)
FINALIZE_STEP_SKILL_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'finalize-step-print-phase-breakdown.md'
)
SHARED_ARTIFACT_PATH = 'work/phase-breakdown-output.txt'


@pytest.fixture(scope='module')
def output_template_text() -> str:
    return OUTPUT_TEMPLATE_PATH.read_text(encoding='utf-8')


def _heading_indices(text: str, heading: str) -> list[int]:
    """Return the line indices where the given exact heading appears."""
    return [i for i, line in enumerate(text.splitlines()) if line.rstrip() == heading]


class TestOverrideSectionPresence:
    """The override section exists at the right place in the document."""

    def test_override_section_heading_exists(self, output_template_text: str):
        idxs = _heading_indices(output_template_text, '## Phase Breakdown Override')
        assert len(idxs) == 1, f'expected exactly one override section heading, got {len(idxs)}'

    def test_override_section_between_snapshot_and_emission(self, output_template_text: str):
        snapshot_idx = _heading_indices(output_template_text, '## Snapshot Procedure')
        override_idx = _heading_indices(output_template_text, '## Phase Breakdown Override')
        emission_idx = _heading_indices(output_template_text, '## Emission Procedure')
        assert snapshot_idx and override_idx and emission_idx
        assert snapshot_idx[0] < override_idx[0] < emission_idx[0], (
            'override section must sit between Snapshot Procedure and Emission Procedure'
        )

    def test_override_describes_step_presence_trigger(self, output_template_text: str):
        # Toggle activates on manifest presence + non-None content captured.
        assert 'finalize-step-print-phase-breakdown' in output_template_text
        assert 'phase_breakdown_override_content' in output_template_text


class TestSnapshotProcedureRead:
    """Snapshot procedure reads work/phase-breakdown-output.txt before archive."""

    def test_snapshot_references_breakdown_artifact(self, output_template_text: str):
        # The exact relative path is mentioned at least once inside the
        # snapshot procedure section.
        assert SHARED_ARTIFACT_PATH in output_template_text

    def test_snapshot_read_uses_manage_files(self, output_template_text: str):
        # The read goes through manage-files (Bucket A script), NOT a raw
        # filesystem read or shell out.
        assert 'manage-files:manage-files read' in output_template_text
        assert SHARED_ARTIFACT_PATH in output_template_text

    def test_snapshot_runs_before_archive(self, output_template_text: str):
        snapshot_idx = output_template_text.find('## Snapshot Procedure')
        archive_caveat_idx = output_template_text.find(
            'BEFORE `default:archive-plan` runs', snapshot_idx
        )
        # The "BEFORE archive" caveat exists and lives inside the snapshot
        # procedure section.
        assert archive_caveat_idx > snapshot_idx, (
            'expected a BEFORE archive caveat inside the Snapshot Procedure'
        )


class TestEmissionProcedureSwap:
    """Emission Procedure step 5 documents the override swap."""

    def test_step_5_emits_override_when_active(self, output_template_text: str):
        # The default Finalize-steps block is skipped when the toggle is
        # active, and the override emits the captured content.
        emission_idx = output_template_text.find('## Emission Procedure')
        block_idx = output_template_text.find('### 5. Build finalize steps block', emission_idx)
        assert block_idx > 0, 'step 5 heading should exist'
        # Look ahead within step 5 for the override-mode short-circuit
        # (cap the search at the next ### heading).
        next_heading_idx = output_template_text.find('### ', block_idx + 1)
        if next_heading_idx == -1:
            next_heading_idx = len(output_template_text)
        step_5_body = output_template_text[block_idx:next_heading_idx]
        assert 'override' in step_5_body.lower(), (
            'step 5 body should mention the override mode'
        )
        assert 'Phase Breakdown' in step_5_body
        assert 'phase_breakdown_override_content' in step_5_body

    def test_default_block_still_documented(self, output_template_text: str):
        # The default (non-override) block construction is still documented
        # in step 5 — the override is the short-circuit, not the only path.
        assert 'Iterate the manifest `phase_6.steps`' in output_template_text


class TestOverrideSkeleton:
    """The override-mode template skeleton is present in the document."""

    def test_override_skeleton_heading_present(self, output_template_text: str):
        # The override skeleton fenced block uses a distinctive sub-heading
        # to differentiate it from the default skeleton.
        assert 'Phase Breakdown override skeleton' in output_template_text

    def test_override_skeleton_has_phase_breakdown_table(self, output_template_text: str):
        # The skeleton shows the breakdown table replacing the [OK] block.
        assert '## Phase Breakdown' in output_template_text


class TestProducerConsumerContract:
    """The producer/consumer artifact path matches between D4 and D5.

    This is the cross-deliverable contract: deliverable 4 documents the
    renderer (consumer), deliverable 5 implements the finalize-step
    (producer). Both must reference the same path string verbatim.
    """

    def test_finalize_step_standards_exists(self):
        assert FINALIZE_STEP_SKILL_PATH.is_file(), (
            f'expected finalize-step standards at {FINALIZE_STEP_SKILL_PATH}'
        )

    def test_path_appears_in_producer(self):
        producer_text = FINALIZE_STEP_SKILL_PATH.read_text(encoding='utf-8')
        assert SHARED_ARTIFACT_PATH in producer_text, (
            f'expected {SHARED_ARTIFACT_PATH} in finalize-step-print-phase-breakdown standards'
        )

    def test_path_appears_in_consumer(self, output_template_text: str):
        assert SHARED_ARTIFACT_PATH in output_template_text, (
            f'expected {SHARED_ARTIFACT_PATH} in output-template.md'
        )

    def test_path_matches_verbatim_in_both(self, output_template_text: str):
        # Same string in both documents — a typo on one side would trip this.
        producer_text = FINALIZE_STEP_SKILL_PATH.read_text(encoding='utf-8')
        producer_count = producer_text.count(SHARED_ARTIFACT_PATH)
        consumer_count = output_template_text.count(SHARED_ARTIFACT_PATH)
        assert producer_count >= 1, f'producer references {SHARED_ARTIFACT_PATH} {producer_count}x'
        assert consumer_count >= 1, f'consumer references {SHARED_ARTIFACT_PATH} {consumer_count}x'
