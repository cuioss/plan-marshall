#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the ``aggregate`` subcommand of manage-lessons.py.

``cmd_aggregate`` is a read-only classifier that groups active lessons that
would land in one plan. The classifier rules (signal priority, primary-pick,
deterministic ordering, merged-body composition) are documented in
``marketplace/bundles/plan-marshall/skills/manage-lessons/references/aggregate-analysis.md``;
this test suite is the executable mirror of that contract.

Cases (a–h) from the originating task description:

- (a) grouping by shared component
- (b) grouping by shared standards directory
- (c) grouping by cross-reference
- (d) overlap with deterministic strongest-signal placement (cross-ref beats
      shared-component)
- (e) primary-pick ordering across cross-ref-fan-in / recurrence-count /
      id ascending
- (f) ``--top-n`` truncation of the headline command list — group composition
      is unaffected, only ``top_n_commands[]`` length
- (g) merged-body composition contains primary body at top followed by H2
      sub-sections in classifier-order
- (h) end-to-end test that runs aggregate against a fixture of 8–12 synthetic
      lessons and asserts the returned TOON shape exactly matches the
      orchestrator's consumption contract documented in aggregate-analysis.md

The tests use Tier 2 (direct import) invocation. Lessons are seeded under
``{tmp_path}/lessons-learned/`` because ``get_lessons_dir()`` resolves
``DIR_LESSONS`` against ``PLAN_BASE_DIR`` (set via ``patch.dict`` for each
test).
"""


from pathlib import Path

from _aggregate_fixtures import _make_lessons_dir, _run_aggregate, _seed_lesson

# =============================================================================
# Case (c) — grouping by cross-reference
# =============================================================================


class TestGroupByCrossRef:
    """Two lessons linked by a cross-ref in their bodies form a cross-ref
    group at the highest tier — case (c).
    """

    def test_two_lessons_cross_ref_form_one_group(self, tmp_path):
        """A cross-ref pair forms a cross-ref group regardless of component.

        Even when the lessons declare distinct components (no shared-component
        match), the body-level cross-reference is sufficient to cluster them
        at the strongest tier. The absorbed-row reason cites the cross-ref.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-301',
            'Lesson Mu',
            component='plan-marshall:phase-1-init',
            body='Mu body references 2025-01-01-01-302 directly.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-302',
            'Lesson Nu',
            component='plan-marshall:phase-2-refine',
            body='Nu body, no refs back.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        assert len(result['groups']) == 1
        group = result['groups'][0]
        assert group['absorb_count'] == 1
        # The cross-ref tier is the only enacted tier.
        assert group['tier'] == 'cross-ref'
        assert group['enacted'] is True
        all_ids = {group['primary_id']} | {row['lesson_id'] for row in group['absorbed']}
        assert all_ids == {'2025-01-01-01-301', '2025-01-01-01-302'}
        for row in group['absorbed']:
            assert row['reason'].startswith('cross-ref to ')


# =============================================================================
# Case (d) — overlap: cross-ref beats shared-component
# =============================================================================


class TestStrongestSignalWins:
    """When two signals would place a lesson in different groups, the
    strongest signal wins — case (d).

    Three lessons:
      - X (component=A) cross-refs Y (component=B)
      - Z (component=A) cross-refs neither

    The strongest-wins rule places X+Y in a cross-ref group and leaves Z
    as a singleton (which is dropped). X is NOT pulled into a
    shared-component group with Z; the cross-ref placement is final.
    """

    def test_cross_ref_placement_excludes_shared_component(self, tmp_path):
        lessons_dir = _make_lessons_dir(tmp_path)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-401',
            'Lesson X',
            component='plan-marshall:phase-1-init',
            body='X body cites 2025-01-01-01-402 once.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-402',
            'Lesson Y',
            component='plan-marshall:phase-2-refine',
            body='Y body, no refs.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-403',
            'Lesson Z',
            component='plan-marshall:phase-1-init',
            body='Z body, no refs and no cross-link to X.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        # Exactly one group, containing X and Y at the cross-ref tier. Z is a
        # singleton at the shared-component tier (X already placed) and is
        # dropped.
        assert len(result['groups']) == 1
        group = result['groups'][0]
        assert group['absorb_count'] == 1
        all_ids = {group['primary_id']} | {row['lesson_id'] for row in group['absorbed']}
        assert all_ids == {'2025-01-01-01-401', '2025-01-01-01-402'}
        # All absorbed reasons cite cross-ref, not shared-component
        for row in group['absorbed']:
            assert row['reason'].startswith('cross-ref to ')


# =============================================================================
# Case (e) — primary-pick ordering
# =============================================================================


class TestPrimaryPick:
    """Primary-pick rule (from aggregate-analysis.md):

    1. Highest cross-ref-fan-in (most other members cite this lesson).
    2. Tie-break: highest recurrence-count (``## Recurrence —`` H2 count).
    3. Tie-break: lowest lesson id ascending.
    """

    def test_fan_in_wins(self, tmp_path):
        """In a 3-member cross-ref group where lesson B is cited by both A
        and C, B is the primary regardless of id ordering.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        # A → B
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-501',
            'Lesson A',
            body='A cites 2025-01-01-01-502.\n',
        )
        # B → (no outgoing refs)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-502',
            'Lesson B',
            body='B body.\n',
        )
        # C → B
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-503',
            'Lesson C',
            body='C cites 2025-01-01-01-502.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        assert len(result['groups']) == 1
        group = result['groups'][0]
        # B has fan-in 2 (cited by A and C); A and C have fan-in 0.
        assert group['primary_id'] == '2025-01-01-01-502'
        # Absorbed rows preserve id-ascending order.
        absorbed_ids = [row['lesson_id'] for row in group['absorbed']]
        assert absorbed_ids == ['2025-01-01-01-501', '2025-01-01-01-503']

    def test_recurrence_breaks_fan_in_tie(self, tmp_path):
        """When fan-in ties, the lesson with more ``## Recurrence —`` H2
        sections wins.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        # P and Q reciprocally cite each other → fan-in 1 each.
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-601',
            'Lesson P',
            body='P cites 2025-01-01-01-602.\n## Recurrence — first\n\n## Recurrence — second\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-602',
            'Lesson Q',
            body='Q cites 2025-01-01-01-601.\n## Recurrence — only one\n',
        )

        result = _run_aggregate(tmp_path)

        group = result['groups'][0]
        # P has 2 recurrences vs Q's 1, breaking the fan-in tie.
        assert group['primary_id'] == '2025-01-01-01-601'

    def test_id_ascending_breaks_remaining_ties(self, tmp_path):
        """When fan-in and recurrence both tie, lowest lesson id wins."""
        lessons_dir = _make_lessons_dir(tmp_path)
        # M and N cite each other; equal recurrence counts (zero).
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-701',
            'Lesson M',
            body='M cites 2025-01-01-01-702.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-702',
            'Lesson N',
            body='N cites 2025-01-01-01-701.\n',
        )

        result = _run_aggregate(tmp_path)

        group = result['groups'][0]
        # M (701) is lexicographically smaller than N (702).
        assert group['primary_id'] == '2025-01-01-01-701'


# =============================================================================
# Case (f) — --top-n truncation of headline command list
# =============================================================================


class TestTopNTruncation:
    """``--top-n`` truncates ONLY the ``top_n_commands[]`` list. Group
    composition (groups[]) is unaffected — every multi-member group is
    always returned regardless of the flag.
    """

    def _seed_three_disjoint_groups(self, tmp_path: Path) -> None:
        """Seed three independent shared-component groups (six lessons)."""
        lessons_dir = _make_lessons_dir(tmp_path)
        # Group 1
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-801',
            'G1 Alpha',
            component='plan-marshall:phase-1-init',
            body='G1 alpha body.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-802',
            'G1 Beta',
            component='plan-marshall:phase-1-init',
            body='G1 beta body.\n',
        )
        # Group 2
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-803',
            'G2 Gamma',
            component='plan-marshall:phase-2-refine',
            body='G2 gamma body.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-804',
            'G2 Delta',
            component='plan-marshall:phase-2-refine',
            body='G2 delta body.\n',
        )
        # Group 3
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-805',
            'G3 Epsilon',
            component='plan-marshall:phase-3-outline',
            body='G3 epsilon body.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-806',
            'G3 Zeta',
            component='plan-marshall:phase-3-outline',
            body='G3 zeta body.\n',
        )

    def test_top_n_one_truncates_commands_only(self, tmp_path):
        """``--top-n 1`` returns all three groups but only one headline command."""
        self._seed_three_disjoint_groups(tmp_path)
        result = _run_aggregate(tmp_path, top_n=1)

        assert result['status'] == 'success'
        assert result['top_n'] == 1
        assert len(result['groups']) == 3  # group composition unaffected
        assert len(result['top_n_commands']) == 1

    def test_top_n_two_truncates_commands_only(self, tmp_path):
        """``--top-n 2`` returns three groups and two headline commands."""
        self._seed_three_disjoint_groups(tmp_path)
        result = _run_aggregate(tmp_path, top_n=2)

        assert result['top_n'] == 2
        assert len(result['groups']) == 3
        assert len(result['top_n_commands']) == 2

    def test_top_n_larger_than_groups_returns_all(self, tmp_path):
        """``--top-n 99`` returns at most one command per group."""
        self._seed_three_disjoint_groups(tmp_path)
        result = _run_aggregate(tmp_path, top_n=99)

        assert result['top_n'] == 99
        assert len(result['groups']) == 3
        # The headline list cannot exceed the number of groups.
        assert len(result['top_n_commands']) == 3
