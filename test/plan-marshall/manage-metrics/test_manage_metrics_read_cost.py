#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


import pytest
from _manage_metrics_fixtures import (
    ns_generate,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _recorded_phase_row,
    cmd_generate,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


class TestReadCostDecomposition:
    """Plan 030 D3: the read cost is published as its two factors — the
    resident-context factor as a PERSISTED field, and the turns factor as the
    existing tool_uses — so a consumer sees the two levers instead of one opaque
    number. The factor is persisted (not a render-time computation) and their
    product reconstructs cache_read_input_tokens.
    """

    def test_resident_context_factor_is_persisted_not_render_only(self, plan_context):
        """generate writes cache_read_per_tool_use = round(cache_read / tool_uses)
        into metrics.toon, so it is readable off the row without re-deriving it."""
        manage_metrics.write_metrics(
            'd3-persist',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'tool_uses': 8,
                        'cache_read_input_tokens': 80000,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('d3-persist'))
        assert result['status'] == 'success'

        five = manage_metrics.read_metrics_raw('d3-persist')['phases']['5-execute']
        # Persisted, and equal to the decomposition factor.
        assert five['cache_read_per_tool_use'] == round(80000 / 8)
        # The product of the two factors reconstructs the read cost exactly here.
        assert five['cache_read_per_tool_use'] * five['tool_uses'] == 80000

    def test_factor_absent_when_tool_uses_is_zero_or_missing(self, plan_context):
        """A guessed factor over a zero/absent turn count is never written."""
        manage_metrics.write_metrics(
            'd3-absent',
            {
                'phases': {
                    # tool_uses absent
                    '3-outline': {
                        'duration_seconds': 100,
                        'cache_read_input_tokens': 5000,
                    },
                    # tool_uses present but zero
                    '5-execute': {
                        'duration_seconds': 200,
                        'tool_uses': 0,
                        'cache_read_input_tokens': 5000,
                    },
                },
            },
        )

        cmd_generate(ns_generate('d3-absent'))
        phases = manage_metrics.read_metrics_raw('d3-absent')['phases']
        assert 'cache_read_per_tool_use' not in phases['3-outline']
        assert 'cache_read_per_tool_use' not in phases['5-execute']

    def test_render_states_the_decomposition_and_discloses_the_population_span(
        self, plan_context
    ):
        """The rendered bullet states the identity and, per D4, names that the ratio
        spans two populations rather than reading as a single-population measure."""
        manage_metrics.write_metrics(
            'd3-render',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'tool_uses': 8,
                        'cache_read_input_tokens': 80000,
                    },
                },
            },
        )

        cmd_generate(ns_generate('d3-render'))
        md = (plan_context.plan_dir_for('d3-render') / 'metrics.md').read_text()
        assert '- **Read-cost decomposition**:' in md
        assert 'resident context per tool-use (10,000)' in md
        assert 'turns (8)' in md
        # D4: the figure names its population span, not a single population.
        assert 'derived-cost ratio' in md
        assert 'the two populations differ' in md

    def test_stale_factor_is_cleared_when_operands_stop_qualifying(self, plan_context):
        """A cache_read_per_tool_use left by an earlier generate is REMOVED (not
        left to render an invalid identity or crash the render) when a later
        generate sees a missing or non-positive tool_uses. Presence is an invariant:
        present iff derivable from this regenerate's operands."""
        # Row seeded WITH a stale factor but a tool_uses that no longer qualifies:
        # one row has tool_uses missing entirely, one has tool_uses == 0.
        manage_metrics.write_metrics(
            'd3-stale',
            {
                'phases': {
                    '3-outline': {
                        'duration_seconds': 100,
                        'cache_read_input_tokens': 5000,
                        'cache_read_per_tool_use': 999,  # stale
                    },
                    '5-execute': {
                        'duration_seconds': 200,
                        'tool_uses': 0,
                        'cache_read_input_tokens': 5000,
                        'cache_read_per_tool_use': 999,  # stale
                    },
                },
            },
        )

        # Must not raise (the old unconditional tool_uses read would KeyError here).
        result = cmd_generate(ns_generate('d3-stale'))
        assert result['status'] == 'success'

        phases = manage_metrics.read_metrics_raw('d3-stale')['phases']
        assert 'cache_read_per_tool_use' not in phases['3-outline']
        assert 'cache_read_per_tool_use' not in phases['5-execute']
        # And the render carries no decomposition bullet for either.
        md = (plan_context.plan_dir_for('d3-stale') / 'metrics.md').read_text()
        assert '- **Read-cost decomposition**:' not in md


def test_unattributed_render_map_covers_every_residual():
    """Contract-drift guard (mirrors the exploration-bucket drift tests): every
    "unattributed" residual among the presence-persisted fields MUST have a
    denominator-bearing render spec, or D1's separation silently regresses to the
    generic label. The render map's key set must equal the DERIVED residual set."""
    assert set(manage_metrics._UNATTRIBUTED_RENDER) == set(
        manage_metrics._UNATTRIBUTED_RESIDUAL_FIELDS
    ), (
        'every unattributed residual field must map to a denominator-bearing '
        'render spec: '
        f'{set(manage_metrics._UNATTRIBUTED_RESIDUAL_FIELDS) ^ set(manage_metrics._UNATTRIBUTED_RENDER)}'
    )
    # The derived set is exactly the two known residuals today; the guard is what
    # keeps a future third residual from bypassing the denominator render.
    assert manage_metrics._UNATTRIBUTED_RESIDUAL_FIELDS == frozenset(
        {'exploration_unattributed_bytes', 'cache_read_unattributed'}
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
