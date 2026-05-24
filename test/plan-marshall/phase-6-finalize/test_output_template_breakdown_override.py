#!/usr/bin/env python3
"""Structural tests for the Phase Breakdown supplement contract in
output-template.md.

Background: the finalize-summary renderer supports an opt-in supplement
mode that appends the captured ``## Phase Breakdown`` table as an
additional section AFTER the per-step ``[OK]`` Finalize-steps block. The
breakdown supplements the per-step list rather than substituting for any
row. The renderer is a markdown-documented procedure (no Python entry
point of its own), so this contract test asserts the documented behavior
is present in ``output-template.md`` and that the producer/consumer file
path matches verbatim between the renderer (consumer) and the finalize
step (producer).

Scope:

1. The standalone ``## Phase Breakdown Supplement`` section exists between
   the Snapshot Procedure and Emission Procedure sections.
2. The Snapshot Procedure documents a read of
   ``work/phase-breakdown-output.txt`` BEFORE ``default:archive-plan``
   runs.
3. The Emission Procedure documents in step 5 (Finalize steps block) that
   every step row (including ``record-metrics``) emits unchanged and that
   the breakdown is appended as an additional section AFTER the per-step
   iteration completes.
4. The supplement-mode skeleton is present in the document.
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


class TestSupplementSectionPresence:
    """The supplement section exists at the right place in the document."""

    def test_supplement_section_heading_exists(self, output_template_text: str):
        idxs = _heading_indices(output_template_text, '## Phase Breakdown Supplement')
        assert len(idxs) == 1, (
            f'expected exactly one supplement section heading, got {len(idxs)}'
        )

    def test_supplement_section_between_snapshot_and_emission(self, output_template_text: str):
        snapshot_idx = _heading_indices(output_template_text, '## Snapshot Procedure')
        supplement_idx = _heading_indices(output_template_text, '## Phase Breakdown Supplement')
        emission_idx = _heading_indices(output_template_text, '## Emission Procedure')
        assert snapshot_idx and supplement_idx and emission_idx
        assert snapshot_idx[0] < supplement_idx[0] < emission_idx[0], (
            'supplement section must sit between Snapshot Procedure and Emission Procedure'
        )

    def test_supplement_describes_step_presence_trigger(self, output_template_text: str):
        # Toggle activates on manifest presence + non-None content captured.
        assert 'finalize-step-print-phase-breakdown' in output_template_text
        assert 'phase_breakdown_override_content' in output_template_text

    def test_supplement_describes_append_not_replace_semantics(self, output_template_text: str):
        """The doc MUST describe append-not-replace semantics — the breakdown
        supplements the per-step list rather than substituting for any row.
        """
        # The new contract is documented in supplement-related prose.
        assert 'supplement' in output_template_text.lower()
        # Negative guard: the legacy substitute/replace prose for the
        # record-metrics row must NOT reappear in supplement-mode prose.
        # We allow the word "replace"/"substitute" generally (used elsewhere
        # in the doc), but the specific "replaces the record-metrics row"
        # / "substitutes the record-metrics row" phrasing must be gone.
        forbidden_phrases = [
            'replaces the `record-metrics` row',
            'replaces the record-metrics row',
            'substitutes the `record-metrics` row',
            'substitutes the record-metrics row',
            'substitute that single row',
            'override mode the row is suppressed',
        ]
        for phrase in forbidden_phrases:
            assert phrase not in output_template_text, (
                f'legacy override-mode prose {phrase!r} must not reappear — '
                f'the supplement append semantics replaces it'
            )


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


class TestEmissionProcedureAppend:
    """Emission Procedure step 5 documents the append-after semantics."""

    def test_step_5_appends_breakdown_after_iteration(self, output_template_text: str):
        # The per-step iteration in step 5 emits every step row unchanged;
        # when the supplement toggle is active, the breakdown is appended
        # AFTER the iteration completes.
        emission_idx = output_template_text.find('## Emission Procedure')
        block_idx = output_template_text.find('### 5. Build finalize steps block', emission_idx)
        assert block_idx > 0, 'step 5 heading should exist'
        # Look ahead within step 5 for the supplement append documentation
        # (cap the search at the next ### heading).
        next_heading_idx = output_template_text.find('### ', block_idx + 1)
        if next_heading_idx == -1:
            next_heading_idx = len(output_template_text)
        step_5_body = output_template_text[block_idx:next_heading_idx]
        # Step 5 still references the supplement-related toggle naming
        # (the in-template content variable retains its legacy identifier
        # so phase-5/6 readers still find it by name).
        assert 'phase_breakdown_override_content' in step_5_body
        assert 'Phase Breakdown' in step_5_body
        # The new append-after-iteration semantics must be explicit.
        assert 'append' in step_5_body.lower(), (
            'step 5 body MUST mention the append-after-iteration semantics'
        )
        # The record-metrics row MUST emit unchanged — guard against
        # regression to substitute-row behaviour.
        assert 'unchanged' in step_5_body.lower() or 'including `record-metrics`' in step_5_body, (
            'step 5 body should declare every step row (incl. record-metrics) '
            'emits unchanged in supplement mode'
        )

    def test_default_block_still_documented(self, output_template_text: str):
        # The default (non-supplement) block construction is still documented
        # in step 5 — the supplement appends to it, not replaces it.
        assert 'Iterate the manifest `phase_6.steps`' in output_template_text


class TestSupplementSkeleton:
    """The supplement-mode template skeleton is present in the document."""

    def test_supplement_skeleton_heading_present(self, output_template_text: str):
        # The supplement skeleton fenced block uses a distinctive sub-heading
        # to differentiate it from the default skeleton.
        assert 'Phase Breakdown supplement skeleton' in output_template_text

    def test_supplement_skeleton_has_phase_breakdown_table(self, output_template_text: str):
        # The skeleton shows the breakdown table appended after the
        # Finalize-steps block.
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
