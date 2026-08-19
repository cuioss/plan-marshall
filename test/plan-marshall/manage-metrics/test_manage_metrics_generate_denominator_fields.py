#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""


import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _pin_start_time_to_past,
    _recorded_phase_row,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
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


class TestGenerateDenominatorFields:
    """`generate` returns each persisted denominator with its sampling point.

    The dedicated behaviour suite lives in `test_denominator_sampling_point.py`;
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


class TestCloseValueScopeDiscriminator:
    """A closed row DECLARES which of its values are cumulative and which are last-close.

    The cumulative-vs-last-close split was previously stated only as prose in
    ``data-format.md`` and two docstrings, so a script consumer reading a
    ``close_count > 1`` row off disk had no field-level signal telling it which
    of the row's values are sums. ``_close_phase_accumulating`` now stamps
    ``value_scope`` on EVERY close, plus ``cumulative_fields`` /
    ``last_close_fields`` from the second close onward — the
    ``total_tokens_population`` precedent (a row-level discriminator with a
    documented absent-reads-as default).
    """

    def test_first_close_stamps_single_close_and_omits_the_field_lists(self, plan_context):
        """One close ⇒ `single_close`, and the two list fields are NOT written.

        On a first close the split is vacuous — every value covers the one and
        only close — so writing the lists would state a distinction the row does
        not have.
        """
        cmd_start_phase(ns_start_phase('vs-first', '5-execute'))
        _pin_start_time_to_past('vs-first', '5-execute')
        cmd_end_phase(ns_end_phase('vs-first', '5-execute', total_tokens=1000, tool_uses=4))

        row = manage_metrics.read_metrics_raw('vs-first')['phases']['5-execute']
        assert row['close_count'] == 1
        assert row['value_scope'] == manage_metrics.VALUE_SCOPE_SINGLE_CLOSE
        assert 'cumulative_fields' not in row
        assert 'last_close_fields' not in row

    def test_second_close_declares_the_split_on_the_row(self, plan_context):
        """A re-entered row names its cumulative and its last-close fields.

        Asserts the concrete field NAMES the row published — not merely that a
        marker appeared — and cross-checks each named cumulative field against
        the arithmetic it claims: `total_tokens` really is the SUM of the two
        closes' deltas, and `close_count` really is 2.
        """
        cmd_start_phase(ns_start_phase('vs-reentry', '5-execute'))
        _pin_start_time_to_past('vs-reentry', '5-execute')
        cmd_end_phase(ns_end_phase('vs-reentry', '5-execute', total_tokens=1000, tool_uses=4))
        # Loop-back: the same phase is closed a second time.
        cmd_end_phase(ns_end_phase('vs-reentry', '5-execute', total_tokens=250, tool_uses=1))

        row = manage_metrics.read_metrics_raw('vs-reentry')['phases']['5-execute']
        assert row['close_count'] == 2
        assert row['value_scope'] == manage_metrics.VALUE_SCOPE_MIXED

        cumulative = row['cumulative_fields'].split(',')
        last_close = row['last_close_fields'].split(',')
        # The declaration names fields the row actually carries, in the module's
        # canonical order.
        assert cumulative == ['close_count', 'duration_seconds', 'total_tokens', 'tool_uses']
        assert last_close == ['start_time', 'end_time']
        # Every declared cumulative field is present on the row it describes.
        for field in cumulative:
            assert field in row, field
        for field in last_close:
            assert field in row, field
        # The claim is true of the values, not only of the labels: both flag
        # values were per-close deltas and were ADDED.
        assert row['total_tokens'] == 1250
        assert row['tool_uses'] == 5

    def test_declaration_never_names_a_field_the_row_lacks(self, plan_context):
        """A close that resolved no token flags declares only what it wrote.

        `_stamp_value_scope` runs as the LAST write of the close and intersects
        with the row's actual keys, so a timestamps-only close (the sanctioned
        inline recording mode) does not claim a `total_tokens` it never wrote.
        """
        cmd_start_phase(ns_start_phase('vs-timestamps', '2-refine'))
        _pin_start_time_to_past('vs-timestamps', '2-refine')
        cmd_end_phase(ns_end_phase('vs-timestamps', '2-refine'))
        cmd_end_phase(ns_end_phase('vs-timestamps', '2-refine'))

        row = manage_metrics.read_metrics_raw('vs-timestamps')['phases']['2-refine']
        assert row['close_count'] == 2
        assert row['value_scope'] == manage_metrics.VALUE_SCOPE_MIXED
        declared = row['cumulative_fields'].split(',')
        assert 'total_tokens' not in declared
        assert 'tool_uses' not in declared
        assert declared == ['close_count', 'duration_seconds']

    def test_re_entered_phase_details_bullet_prints_the_rows_own_declaration(
        self, plan_context
    ):
        """metrics.md renders the row's field lists rather than restating them.

        A hand-restated list at the render site would be a second copy free to
        drift from the writer's, so the bullet is asserted to carry the exact
        strings the row published.
        """
        cmd_start_phase(ns_start_phase('vs-md', '5-execute'))
        _pin_start_time_to_past('vs-md', '5-execute')
        cmd_end_phase(ns_end_phase('vs-md', '5-execute', total_tokens=1000, tool_uses=4))
        cmd_end_phase(ns_end_phase('vs-md', '5-execute', total_tokens=250, tool_uses=1))
        cmd_generate(ns_generate('vs-md'))

        row = manage_metrics.read_metrics_raw('vs-md')['phases']['5-execute']
        md = (plan_context.plan_dir_for('vs-md') / 'metrics.md').read_text()
        bullet = next(line for line in md.splitlines() if line.startswith('- **Closes**'))
        assert '2' in bullet
        assert f'Cumulative across closes: {row["cumulative_fields"]}' in bullet
        assert f'Latest close only: {row["last_close_fields"]}' in bullet


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
