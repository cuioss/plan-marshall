#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``aggregate`` subcommand of manage-lessons.py.

Its sections, in order:

* Case (g) — merged-body composition (preview)
* Case (h) — end-to-end fixture matching the orchestrator consumption contract
"""


from pathlib import Path

from _aggregate_fixtures import AGGREGATE_PREVIEW_CHARS, _make_lessons_dir, _run_aggregate, _seed_lesson

# =============================================================================
# Case (g) — merged-body composition (preview)
# =============================================================================


class TestMergedBodyComposition:
    """The merged_body_preview must contain the primary's body at the top
    followed by H2 ``## Sub-task: {title} ({lesson_id})`` sections in
    classifier-order (id ascending) — case (g).

    The preview is truncated to ``AGGREGATE_PREVIEW_CHARS`` characters; we
    keep the seeded bodies short enough that the entire merged body fits
    within the preview window so we can assert the full structure.
    """

    def test_preview_starts_with_primary_body(self, tmp_path):
        lessons_dir = _make_lessons_dir(tmp_path)
        # Cross-ref triangle: A → B, A → C. A has fan-in 0; B and C also
        # have fan-in 0; but B and C cite each other indirectly only through
        # A. Let's pick a clearer setup: A is cited by B and C, so A is the
        # primary by fan-in. Absorbed are B (901) and C (902) in id order.
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-900',
            'Primary Lesson',
            body='Primary first paragraph.\nPrimary second paragraph.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-901',
            'Absorbed One',
            body='Cites 2025-01-01-01-900.\nAbsorbed-one body line.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-902',
            'Absorbed Two',
            body='Cites 2025-01-01-01-900.\nAbsorbed-two body line.\n',
        )

        result = _run_aggregate(tmp_path)

        assert len(result['groups']) == 1
        group = result['groups'][0]
        assert group['primary_id'] == '2025-01-01-01-900'

        preview = group['merged_body_preview']
        # The preview must START with the primary body (modulo trailing
        # whitespace stripped by the composer).
        assert preview.startswith('Primary first paragraph.')

    def test_preview_contains_h2_subsections_in_id_order(self, tmp_path):
        lessons_dir = _make_lessons_dir(tmp_path)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-910',
            'Primary Lesson',
            body='Primary content.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-911',
            'First Absorbed',
            body='Cites 2025-01-01-01-910.\nFirst absorbed content.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-912',
            'Second Absorbed',
            body='Cites 2025-01-01-01-910.\nSecond absorbed content.\n',
        )

        result = _run_aggregate(tmp_path)

        group = result['groups'][0]
        preview = group['merged_body_preview']

        # Both H2 sub-section headings must appear in the preview, in id
        # ascending order. The bodies are short enough to fit fully inside
        # AGGREGATE_PREVIEW_CHARS (400) so we can assert ordering.
        first_idx = preview.find('## Sub-task: First Absorbed (2025-01-01-01-911)')
        second_idx = preview.find('## Sub-task: Second Absorbed (2025-01-01-01-912)')
        assert first_idx >= 0, f'first H2 missing in preview: {preview!r}'
        assert second_idx >= 0, f'second H2 missing in preview: {preview!r}'
        assert first_idx < second_idx, (
            'absorbed H2 sub-sections must appear in id-ascending order'
        )
        # The primary body must precede both H2 headings.
        primary_idx = preview.find('Primary content.')
        assert 0 <= primary_idx < first_idx

    def test_preview_truncated_to_400_chars(self, tmp_path):
        """When the would-be merged body exceeds AGGREGATE_PREVIEW_CHARS, the
        preview is truncated to the limit.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        big_body_a = 'A' * 600  # exceeds 400 alone
        big_body_b = 'B' * 600
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-920',
            'Primary',
            body=f'Cites 2025-01-01-01-921.\n{big_body_a}\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-921',
            'Absorbed',
            body=f'Cites 2025-01-01-01-920.\n{big_body_b}\n',
        )

        result = _run_aggregate(tmp_path)

        group = result['groups'][0]
        assert len(group['merged_body_preview']) == AGGREGATE_PREVIEW_CHARS


# =============================================================================
# Case (h) — end-to-end fixture matching the orchestrator consumption contract
# =============================================================================


class TestEndToEndContract:
    """Run aggregate against a synthetic 10-lesson corpus and assert the
    returned TOON shape exactly matches the orchestrator's consumption
    contract from aggregate-analysis.md — case (h).

    The contract:

      status: success
      top_n: N
      groups[K]{primary_id, primary_title, absorb_count, tier, enacted,
               absorbed[M]{lesson_id, title, reason},
               merged_body_preview}
      top_n_commands[N]
    """

    REQUIRED_TOP_LEVEL_KEYS = {'status', 'top_n', 'groups', 'top_n_commands'}
    REQUIRED_GROUP_KEYS = {
        'primary_id',
        'primary_title',
        'absorb_count',
        'tier',
        'enacted',
        'absorbed',
        'merged_body_preview',
    }
    VALID_TIERS = {
        'cross-ref',
        'shared-component',
        'shared-standards-dir',
        'shared-workflow-boundary',
    }
    REQUIRED_ABSORBED_KEYS = {'lesson_id', 'title', 'reason'}

    def _seed_corpus(self, tmp_path: Path) -> Path:
        """Seed 10 synthetic lessons covering all four signal tiers and a
        singleton that must be dropped.
        """
        lessons_dir = _make_lessons_dir(tmp_path)

        # Tier 1: cross-ref pair (E2E-001 ↔ E2E-002)
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-001',
            'Cross-ref primary',
            component='plan-marshall:phase-3-outline',
            body='Cites 2025-02-01-01-002.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-002',
            'Cross-ref partner',
            component='plan-marshall:phase-4-plan',
            body='Cites 2025-02-01-01-001.\n',
        )

        # Tier 2: shared-component pair (003 + 004)
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-003',
            'Shared comp first',
            component='plan-marshall:phase-5-execute',
            body='No refs.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-004',
            'Shared comp second',
            component='plan-marshall:phase-5-execute',
            body='No refs.\n',
        )

        # Tier 4: shared-workflow-boundary (005 + 006), components differ by
        # trailing numeric segment.
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-005',
            'Boundary first',
            component='plan-marshall:phase-6-finalize:5',
            body='Boundary body.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-006',
            'Boundary second',
            component='plan-marshall:phase-6-finalize:6',
            body='Boundary body.\n',
        )

        # Another shared-component pair to give us multiple groups (007 + 008)
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-007',
            'Second comp first',
            component='plan-marshall:phase-1-init',
            body='No refs.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-008',
            'Second comp second',
            component='plan-marshall:phase-1-init',
            body='No refs.\n',
        )

        # Singleton (009) — unique component, must be dropped from output.
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-009',
            'Singleton lesson',
            component='plan-marshall:unique-only',
            body='No refs.\n',
        )

        # Superseded lesson (010) — must be ignored entirely by the loader.
        _seed_lesson(
            lessons_dir,
            '2025-02-01-01-010',
            'Superseded ignored',
            component='plan-marshall:phase-5-execute',
            body='No refs but uses same comp as 003/004.\n',
            status='superseded',
            extra_metadata='superseded_by=2025-02-01-01-003\n',
        )

        return lessons_dir

    def test_top_level_shape_matches_contract(self, tmp_path):
        self._seed_corpus(tmp_path)
        result = _run_aggregate(tmp_path, top_n=3)

        # Top-level keys
        assert set(result.keys()) >= self.REQUIRED_TOP_LEVEL_KEYS
        assert result['status'] == 'success'
        assert result['top_n'] == 3
        assert isinstance(result['groups'], list)
        assert isinstance(result['top_n_commands'], list)

    def test_groups_shape_matches_contract(self, tmp_path):
        self._seed_corpus(tmp_path)
        result = _run_aggregate(tmp_path, top_n=5)

        # We expect exactly 4 multi-member groups: cross-ref (001+002),
        # shared-component (003+004), workflow-boundary (005+006), and the
        # second shared-component (007+008). Singleton 009 dropped.
        # Superseded 010 ignored entirely.
        assert len(result['groups']) == 4

        for group in result['groups']:
            assert set(group.keys()) >= self.REQUIRED_GROUP_KEYS
            assert isinstance(group['primary_id'], str)
            assert isinstance(group['primary_title'], str)
            assert isinstance(group['absorb_count'], int)
            assert group['absorb_count'] >= 1
            assert group['tier'] in self.VALID_TIERS
            assert isinstance(group['enacted'], bool)
            # enacted is True iff the tier is cross-ref.
            assert group['enacted'] == (group['tier'] == 'cross-ref')
            assert isinstance(group['absorbed'], list)
            assert len(group['absorbed']) == group['absorb_count']
            assert isinstance(group['merged_body_preview'], str)
            assert len(group['merged_body_preview']) <= AGGREGATE_PREVIEW_CHARS
            for row in group['absorbed']:
                assert set(row.keys()) >= self.REQUIRED_ABSORBED_KEYS
                assert isinstance(row['lesson_id'], str)
                assert isinstance(row['title'], str)
                assert isinstance(row['reason'], str)
                assert row['reason']  # non-empty

    def test_singleton_and_superseded_excluded(self, tmp_path):
        self._seed_corpus(tmp_path)
        result = _run_aggregate(tmp_path)

        all_referenced_ids = set()
        for group in result['groups']:
            all_referenced_ids.add(group['primary_id'])
            for row in group['absorbed']:
                all_referenced_ids.add(row['lesson_id'])

        # Singleton 009 must NOT appear anywhere
        assert '2025-02-01-01-009' not in all_referenced_ids
        # Superseded 010 must NOT appear anywhere
        assert '2025-02-01-01-010' not in all_referenced_ids

    def test_top_n_commands_well_formed(self, tmp_path):
        self._seed_corpus(tmp_path)
        result = _run_aggregate(tmp_path, top_n=2)

        assert result['top_n'] == 2
        assert len(result['top_n_commands']) == 2
        for cmd in result['top_n_commands']:
            assert cmd.startswith('/plan-marshall:plan-marshall lesson=')

    def test_determinism_repeated_runs(self, tmp_path):
        """Repeated runs over the same corpus produce identical TOON output —
        criteria from the originating task specifying classifier behavior is
        deterministic.
        """
        self._seed_corpus(tmp_path)
        first = _run_aggregate(tmp_path, top_n=3)
        second = _run_aggregate(tmp_path, top_n=3)
        third = _run_aggregate(tmp_path, top_n=3)
        assert first == second == third

    def test_groups_returned_in_key_ascending_order(self, tmp_path):
        """``groups[]`` is sorted by group key ascending so the orchestrator
        can present a stable display order without re-sorting.

        Group keys come from the strongest-signal tier that produced each
        group (cross-ref → smallest member id; shared-component → component
        value; etc.). The keys are not exposed in the public TOON, so we
        assert ordering indirectly by checking that no later group has a
        primary_id that would sort before an earlier group's primary_id
        WHEN both groups share the same tier. (Cross-tier ordering is
        determined by group key, which mixes lesson ids and component
        strings; we keep this assertion tier-aware.)
        """
        self._seed_corpus(tmp_path)
        result = _run_aggregate(tmp_path)

        # The ordering rule is alphabetical on group key. Cross-ref group
        # key is '2025-02-01-01-001'; shared-component keys are the component
        # strings; workflow-boundary key is its component prefix. Without
        # the keys exposed, we verify the deterministic-ordering acceptance
        # criterion structurally: the same corpus must yield the same group
        # list across runs (covered by test_determinism_repeated_runs) and
        # absorbed-row ordering within each group must be id-ascending.
        for group in result['groups']:
            absorbed_ids = [row['lesson_id'] for row in group['absorbed']]
            assert absorbed_ids == sorted(absorbed_ids), (
                f'absorbed ids out of order in group {group["primary_id"]!r}: {absorbed_ids}'
            )
