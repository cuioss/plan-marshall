#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _UNSEEDED_PLAN_IDS,
    _phase_breakdown_header,
    _seed_billing_phases,
    _seed_guarded_plan_dirs,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)


class TestGenerateReEntryMarker:
    """generate surfaces ``close_count > 1`` as a first-class re-entry marker.

    Because the write site now accumulates across closes, a re-entered phase's
    totals are sums and a reader must be told which rows those are. ``close_count``
    is written at the write site, so the marker needs no timestamp inference — and
    unlike the ``boundary_monotonicity`` warning it names the phase that was
    actually re-entered. The signal surfaces in three places: the ``generate``
    return, a top-level ``re_entered_phases`` key in ``metrics.toon``, and a
    ``> Re-entered phases: …`` marker plus a per-phase **Closes** bullet in
    ``metrics.md``. A once-closed phase surfaces none of them.
    """

    @staticmethod
    def _closed_row(start: str, end: str, wall_s: float, close_count: int, tokens: int = 1000) -> dict:
        return {
            'start_time': start,
            'end_time': end,
            'duration_seconds': wall_s,
            'total_tokens': tokens,
            'close_count': close_count,
        }

    def test_reentered_phase_renders_marker_bullet_and_key(self, plan_context):
        """A close_count=2 row is named in the marker, the bullet, and the return key."""
        manage_metrics.write_metrics(
            'reentry-marker',
            {
                'phases': {
                    '5-execute': self._closed_row(
                        '2026-05-08T14:00:00+00:00', '2026-05-08T14:03:20+00:00', 300.0, 2, tokens=3000
                    ),
                    '6-finalize': self._closed_row(
                        '2026-05-08T15:00:00+00:00', '2026-05-08T15:10:00+00:00', 600.0, 1
                    ),
                },
            },
        )

        result = cmd_generate(ns_generate('reentry-marker'))
        assert result['status'] == 'success'
        assert result['re_entered_phases'] == ['5-execute']

        toon = (plan_context.plan_dir_for('reentry-marker') / 'work' / 'metrics.toon').read_text()
        assert 're_entered_phases: 5-execute' in toon

        md = (plan_context.plan_dir_for('reentry-marker') / 'metrics.md').read_text()
        assert '> Re-entered phases: 5-execute' in md
        # The per-phase bullet fires only for the re-entered row — a once-closed
        # phase carries no reader-relevant close-count fact.
        assert '- **Closes**: 2' in md
        assert '- **Closes**: 1' not in md

        # The marker sits between the heading and the breakdown table header row,
        # consistent with the neighbouring `> Partial:` marker's placement.
        md_lines = md.splitlines()
        heading_idx = md_lines.index('## Phase Breakdown')
        marker_idx = next(i for i, line in enumerate(md_lines) if line.startswith('> Re-entered phases:'))
        header_idx = next(i for i, line in enumerate(md_lines) if line.startswith('| Phase'))
        assert heading_idx < marker_idx < header_idx

    def test_once_closed_phase_renders_neither_marker_nor_bullet(self, plan_context):
        """A plan whose every phase closed once emits no marker, bullet, or key."""
        manage_metrics.write_metrics(
            'reentry-none',
            {
                'phases': {
                    '5-execute': self._closed_row(
                        '2026-05-08T14:00:00+00:00', '2026-05-08T14:03:20+00:00', 200.0, 1
                    ),
                },
            },
        )

        result = cmd_generate(ns_generate('reentry-none'))
        assert result['status'] == 'success'
        assert result['re_entered_phases'] == []

        toon = (plan_context.plan_dir_for('reentry-none') / 'work' / 'metrics.toon').read_text()
        assert 're_entered_phases' not in toon

        md = (plan_context.plan_dir_for('reentry-none') / 'metrics.md').read_text()
        assert '> Re-entered phases:' not in md
        assert '- **Closes**' not in md

    def test_multiple_reentered_phases_listed_in_canonical_order(self, plan_context):
        """re_entered_phases follows canonical phase order, not insertion order."""
        manage_metrics.write_metrics(
            'reentry-order',
            {
                'phases': {
                    # Inserted 5-execute first so insertion order differs from canonical.
                    '5-execute': self._closed_row(
                        '2026-05-08T14:00:00+00:00', '2026-05-08T14:10:00+00:00', 600.0, 3
                    ),
                    '2-refine': self._closed_row(
                        '2026-05-08T12:00:00+00:00', '2026-05-08T12:10:00+00:00', 600.0, 2
                    ),
                },
            },
        )

        result = cmd_generate(ns_generate('reentry-order'))
        assert result['re_entered_phases'] == ['2-refine', '5-execute']

        md = (plan_context.plan_dir_for('reentry-order') / 'metrics.md').read_text()
        assert '> Re-entered phases: 2-refine, 5-execute' in md
        assert '- **Closes**: 3' in md
        assert '- **Closes**: 2' in md

    def test_legacy_row_without_close_count_is_not_reported_as_reentered(self, plan_context):
        """A pre-fix row carrying no close_count reads as 0 and is never named.

        Archived plans predate the counter, so an absent field must not be
        mistaken for a re-entry — the corpus damage assessment relies on
        ``close_count`` being genuinely absent rather than defaulted upward.
        """
        manage_metrics.write_metrics(
            'reentry-legacy',
            {
                'phases': {
                    '5-execute': {
                        'start_time': '2026-05-08T14:00:00+00:00',
                        'end_time': '2026-05-08T14:10:00+00:00',
                        'duration_seconds': 600.0,
                        'total_tokens': 1000,
                    },
                },
            },
        )

        result = cmd_generate(ns_generate('reentry-legacy'))
        assert result['re_entered_phases'] == []

        md = (plan_context.plan_dir_for('reentry-legacy') / 'metrics.md').read_text()
        assert '> Re-entered phases:' not in md
        assert '- **Closes**' not in md


def test_generate_returns_total_billing_weighted(plan_context):
    """The cost aggregate is returned as its own field, never folded into tokens."""
    plan_id = 'billing-return'
    _seed_billing_phases(plan_id, {'4-plan': 41003, '5-execute': 78000})

    result = cmd_generate(ns_generate(plan_id))

    assert result['total_billing_weighted'] == 119003
    # The dispatched work total is the tokens sum, untouched by the cost figure.
    assert result['total_tokens'] == 20000


def test_tokens_column_header_names_a_default_not_a_single_population(plan_context):
    """The Tokens header states a DEFAULT population plus the marking convention.

    The column is not single-population — an inline phase's cell carries a
    main-context-window figure — so a bare ``Tokens (dispatched)`` would assert
    over a mixed column exactly the single-population claim this report exists
    to stop making. The header must name the default AND signal that exceptions
    are marked.
    """
    cmd_start_phase(ns_start_phase('metrics-header-default', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-header-default', '1-init', total_tokens=1000))
    cmd_generate(ns_generate('metrics-header-default'))

    header = _phase_breakdown_header(
        (plan_context.plan_dir_for('metrics-header-default') / 'metrics.md').read_text()
    )
    tokens_col = [c.strip() for c in header.strip('|').split('|')][4]
    assert tokens_col == 'Tokens (dispatched unless marked)'
    # The population is named, and it is named as a default rather than as an
    # unqualified property of every cell in the column.
    assert 'dispatched' in tokens_col
    assert 'unless marked' in tokens_col
    assert tokens_col != 'Tokens (dispatched)'


def test_worked_le_wall_invariant_holds_for_subagent_dispatching_phases(plan_context):
    """Worked <= Reported (wall) invariant — holds for every phase that
    dispatches a subagent within the phase window.

    Three subagent-dispatching phases (1-init, 3-outline, 5-execute) are
    seeded with overlapping agent + subagent attribution spans. After the
    fix, every per-phase worked value MUST be <= the corresponding wall
    value and Idle MUST be non-blank (non-zero) for each.
    """
    manage_metrics.write_metrics(
        'metrics-invariant',
        {
            'phases': {
                '1-init': {
                    'duration_seconds': 200,
                    'agent_duration_ms': 80000,
                    'subagent_duration_ms': 150000,
                },
                '3-outline': {
                    'duration_seconds': 400,
                    'agent_duration_ms': 120000,
                    'subagent_duration_ms': 250000,
                },
                '5-execute': {
                    'duration_seconds': 900,
                    'agent_duration_ms': 300000,
                    'subagent_duration_ms': 600000,
                },
            },
        },
    )

    result = cmd_generate(ns_generate('metrics-invariant'))
    assert result['status'] == 'success'

    toon = (plan_context.plan_dir_for('metrics-invariant') / 'work' / 'metrics.toon').read_text()
    # Per-phase invariant: worked = max(agent, subagent), idle = wall - worked.
    # 1-init: worked=150s, wall=200s, idle=50s.
    # 3-outline: worked=250s, wall=400s, idle=150s.
    # 5-execute: worked=600s, wall=900s, idle=300s.
    assert 'idle_duration_ms: 50000' in toon
    assert 'idle_duration_ms: 150000' in toon
    assert 'idle_duration_ms: 300000' in toon

    # Total worked never exceeds total wall.
    assert result['total_worked_seconds'] <= result['total_wall_seconds']
    # Total idle is the residual.
    assert result['total_idle_seconds'] == (
        result['total_wall_seconds'] - result['total_worked_seconds']
    )
