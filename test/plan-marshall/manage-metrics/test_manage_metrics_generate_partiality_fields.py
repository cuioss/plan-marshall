#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Scope: the missing-end-time partiality pair — what ``generate`` returns, what
reaches metrics.toon, and the marker the report renders.
"""


from _manage_metrics_fixtures import (
    ns_generate,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _recorded_phase_row,
    _seed_guarded_plan_dirs,
    cmd_generate,
    manage_metrics,
)


class TestGeneratePartialityFields:
    """generate publishes the end_time-presence check across all three surfaces.

    ``generate`` derives ``any_phase_missing_end_time`` (true whenever a canonical
    phase's row carries no ``end_time``) and ``phases_missing_end_time`` (the
    offending canonical phases in phase order). Both surface in three places: the
    ``generate`` return TOON, two top-level keys in ``metrics.toon``, and a
    ``> Phases missing an end_time boundary marker — …`` line rendered under the
    ``## Phase Breakdown`` heading. A plan whose six rows all carry ``end_time``
    reports ``false`` with an empty list and renders no line.

    The keys are named for the PREDICATE, not for a completeness verdict — the
    check reads ``end_time`` and nothing else, and the retired ``partial`` /
    ``unrecorded_phases`` names asserted more than that. The rename is breaking:
    the writer emits the new keys only.
    """

    def test_return_toon_reports_missing_end_time_marker(self, plan_context):
        """A plan whose 6-finalize never closed reports the phase in the return."""
        # Canonical under-count: the first five phases are closed but 6-finalize
        # never had its boundary recorded (interrupt / loop-back / never-reached).
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics('partial-true-return', {'phases': phases})

        result = cmd_generate(ns_generate('partial-true-return'))
        assert result['status'] == 'success'
        assert result['any_phase_missing_end_time'] is True
        assert result['phases_missing_end_time'] == ['6-finalize']

    def test_return_toon_end_time_fields_are_bool_and_list(self, plan_context):
        """The return carries the bool as a bool and the phase list as a list."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:3]}
        manage_metrics.write_metrics('partial-types', {'phases': phases})

        result = cmd_generate(ns_generate('partial-types'))
        assert isinstance(result['any_phase_missing_end_time'], bool)
        assert isinstance(result['phases_missing_end_time'], list)

    def test_every_row_carrying_end_time_reports_false(self, plan_context):
        """All six canonical rows carrying end_time reports False, empty list."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('partial-false-full', {'phases': phases})

        result = cmd_generate(ns_generate('partial-false-full'))
        assert result['status'] == 'success'
        assert result['any_phase_missing_end_time'] is False
        assert result['phases_missing_end_time'] == []

    def test_missing_end_time_phases_listed_in_canonical_order(self, plan_context):
        """phases_missing_end_time preserves canonical order, not insertion order."""
        # Record only 3-outline and 5-execute; the other four carry no end_time.
        recorded = {'3-outline', '5-execute'}
        phases = {name: _recorded_phase_row() for name in recorded}
        manage_metrics.write_metrics('partial-order', {'phases': phases})

        result = cmd_generate(ns_generate('partial-order'))
        assert result['any_phase_missing_end_time'] is True
        expected = [name for name in manage_metrics.PHASE_NAMES if name not in recorded]
        assert result['phases_missing_end_time'] == expected
        assert result['phases_missing_end_time'] == ['1-init', '2-refine', '4-plan', '6-finalize']

    def test_row_without_end_time_is_listed(self, plan_context):
        """The predicate keys on end_time — a started-but-unclosed row is listed.

        Distinguishes "phase has a row" from "phase carries the boundary marker":
        4-plan carries a start_time but no end_time, so it must appear in
        phases_missing_end_time even though its row exists.
        """
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        # Strip 4-plan's end_time: a row present but never boundary-closed.
        phases['4-plan'] = {'start_time': '2020-01-01T00:00:00+00:00', 'duration_seconds': 600}
        manage_metrics.write_metrics('partial-unclosed-row', {'phases': phases})

        result = cmd_generate(ns_generate('partial-unclosed-row'))
        assert result['any_phase_missing_end_time'] is True
        assert result['phases_missing_end_time'] == ['4-plan']

    def test_end_time_fields_persisted_to_metrics_toon(self, plan_context):
        """Both renamed keys land as top-level keys in metrics.toon."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics('partial-toon', {'phases': phases})

        cmd_generate(ns_generate('partial-toon'))

        # Parsed top-level keys (written before the first [phase] block).
        data = manage_metrics.read_metrics_raw('partial-toon')
        assert data['any_phase_missing_end_time'] == 'true'
        assert data['phases_missing_end_time'] == '6-finalize'

        # The literal tokens are present in the file (round-trip target).
        toon = (plan_context.plan_dir_for('partial-toon') / 'work' / 'metrics.toon').read_text()
        assert 'any_phase_missing_end_time: true' in toon
        assert 'phases_missing_end_time: 6-finalize' in toon

    def test_all_end_times_present_persists_false_and_empty_list(self, plan_context):
        """A plan whose rows all carry end_time persists false with an empty list."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('partial-toon-false', {'phases': phases})

        cmd_generate(ns_generate('partial-toon-false'))

        data = manage_metrics.read_metrics_raw('partial-toon-false')
        assert data['any_phase_missing_end_time'] == 'false'
        assert data['phases_missing_end_time'] == ''
        toon = (plan_context.plan_dir_for('partial-toon-false') / 'work' / 'metrics.toon').read_text()
        assert 'any_phase_missing_end_time: false' in toon

    def test_writer_emits_new_keys_only_and_drops_the_retired_pair(self, plan_context):
        """A metrics.toon carrying the RETIRED keys loses them on regenerate.

        `compatibility: breaking`, no dual-key shim. `read_metrics_raw`
        round-trips arbitrary top-level keys, so without the write-side refusal a
        regenerate would leave the stale `partial` / `unrecorded_phases` pair
        sitting beside the new keys and a reader could take the stale pair as
        current. The evidence asserted is the ABSENCE of both retired literals
        from the rewritten file, not merely the presence of the new ones.
        """
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics(
            'partial-retired-drop',
            {'phases': phases, 'partial': 'false', 'unrecorded_phases': ''},
        )
        seeded = (
            plan_context.plan_dir_for('partial-retired-drop') / 'work' / 'metrics.toon'
        ).read_text()
        # Guard the fixture itself: the retired pair really is on disk pre-generate.
        assert 'partial: false' in seeded
        assert 'unrecorded_phases: ' in seeded

        cmd_generate(ns_generate('partial-retired-drop'))

        data = manage_metrics.read_metrics_raw('partial-retired-drop')
        assert 'partial' not in data
        assert 'unrecorded_phases' not in data
        assert data['any_phase_missing_end_time'] == 'true'
        assert data['phases_missing_end_time'] == '6-finalize'

        toon = (
            plan_context.plan_dir_for('partial-retired-drop') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'partial: false' not in toon
        assert 'unrecorded_phases:' not in toon

    def test_metrics_md_marker_renders_under_phase_breakdown_heading(self, plan_context):
        """The marker line renders between the ## Phase Breakdown heading and the table."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics('partial-md-marker', {'phases': phases})

        cmd_generate(ns_generate('partial-md-marker'))

        md = (plan_context.plan_dir_for('partial-md-marker') / 'metrics.md').read_text()
        md_lines = md.splitlines()
        marker_idx = next(
            i
            for i, line in enumerate(md_lines)
            if line.startswith('> Phases missing an end_time boundary marker')
        )
        marker = md_lines[marker_idx]
        # The line NAMES the offending phase and the predicate it checked, and
        # explicitly disclaims the wider verdict the retired name asserted.
        assert '6-finalize' in marker
        assert 'end_time-presence check only' in marker
        assert 'complete or internally consistent' in marker
        # The retired marker wording is gone entirely.
        assert '> Partial:' not in md

        heading_idx = md_lines.index('## Phase Breakdown')
        header_idx = next(i for i, line in enumerate(md_lines) if line.startswith('| Phase'))
        # Marker sits after the heading and before the breakdown table header row.
        assert heading_idx < marker_idx < header_idx

    def test_all_end_times_present_renders_no_marker(self, plan_context):
        """A plan whose rows all carry end_time renders no marker in metrics.md."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('partial-md-none', {'phases': phases})

        cmd_generate(ns_generate('partial-md-none'))

        md = (plan_context.plan_dir_for('partial-md-none') / 'metrics.md').read_text()
        assert '> Phases missing an end_time boundary marker' not in md
        assert '> Partial:' not in md


class TestGenerateDenominatorFields:
    """`generate` returns each persisted denominator with its sampling point.

    The dedicated behaviour suites live in `test_denominator_absence_versus_zero.py`
    and `test_denominator_sampling_point_persistence.py`;
    these two cases pin the `generate` OUTPUT surface itself — that the pair
    reaches the return, and that an undeterminable denominator is omitted from
    it rather than defaulted, exactly as it is from the record.
    """

    def test_return_carries_the_denominator_pair(self, plan_context):
        """A plan with a readable outline returns the count AND its sampling point."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('gen-denominator', {'phases': phases})
        plan_dir = plan_context.plan_dir_for('gen-denominator')
        # The headings live under `## Deliverables` because that is where the
        # solution-outline standard puts them, and the only scope the
        # authoritative extractor `generate` delegates to looks at.
        (plan_dir / 'solution_outline.md').write_text(
            '## Deliverables\n\n### 1. First\n\n### 2. Second\n', encoding='utf-8'
        )

        result = cmd_generate(ns_generate('gen-denominator'))

        assert result['deliverable_count'] == 2
        assert result['deliverable_count_sampling_point'] == (
            manage_metrics.SAMPLING_POINT_GENERATE_TIME
        )
        assert result['denominators_sampled_at']

    def test_return_omits_a_denominator_that_could_not_be_counted(self, plan_context):
        """No source ⇒ the key is ABSENT from the return, never a 0.

        The matched negative control for the test above: without it, an
        unconditional zero-fill would satisfy the positive assertions while
        asserting a count the plan never had.
        """
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('gen-denominator-absent', {'phases': phases})

        result = cmd_generate(ns_generate('gen-denominator-absent'))

        assert result['status'] == 'success', result
        for name in ('deliverable_count', 'files_modified', 'tasks_completed'):
            assert name not in result, name
            assert f'{name}_sampling_point' not in result, name
        assert 'denominators_sampled_at' not in result
