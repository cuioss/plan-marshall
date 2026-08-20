#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The rendered report and the store agree about what exists."""


from datetime import UTC, datetime, timedelta

from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _persisted_aggregate_round_trip_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _TOTAL_COLUMNS,
    _drive_two_dispatched_phases,
    _phase_field,
    _report,
    _seed_guarded_plan_dirs,
    _store,
    _top_level_field,
    _total_row_cells,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)


class TestPersistedAggregate:
    """Every figure the Total row renders is locatable in the store."""

    def test_every_rendered_total_has_a_persisted_counterpart(self, plan_context):
        """The round trip: no Total cell is a figure only the render knows."""
        _drive_two_dispatched_phases('agg-round-trip')
        cmd_generate(ns_generate('agg-round-trip'))

        store = _store(plan_context, 'agg-round-trip')
        for column in _TOTAL_COLUMNS:
            field = manage_metrics._TOTALS_FIELDS[column]
            count_field = f'{field}{manage_metrics._POPULATION_COUNT_SUFFIX}'
            assert _top_level_field(store, field) is not None, f'{field} not persisted'
            assert _top_level_field(store, count_field) is not None, f'{count_field} not persisted'
        assert _top_level_field(store, manage_metrics._TOTALS_DENOMINATOR_FIELD) == '6'

    def test_persisted_token_total_equals_the_rendered_one(self, plan_context):
        """The store's figure IS the report's figure, not a parallel derivation."""
        _drive_two_dispatched_phases('agg-same-number')
        cmd_generate(ns_generate('agg-same-number'))

        store = _store(plan_context, 'agg-same-number')
        rendered = _total_row_cells(_report(plan_context, 'agg-same-number'))[4]

        assert _top_level_field(store, 'totals_tokens') == '100000'
        assert rendered.startswith('100,000')

    def test_population_qualifier_is_persisted_not_only_rendered(self, plan_context):
        """The `(n=k/N)` marker's k and N both exist as fields.

        The qualifier is what separates a sum over 2 of 6 phases from a sum over
        6 of 6 — two different quantities that render identically without it.
        """
        _drive_two_dispatched_phases('agg-qualifier')
        cmd_generate(ns_generate('agg-qualifier'))

        store = _store(plan_context, 'agg-qualifier')
        rendered = _total_row_cells(_report(plan_context, 'agg-qualifier'))[4]

        assert '(n=2/6)' in rendered
        assert _top_level_field(store, 'totals_tokens_population_count') == '2'
        assert _top_level_field(store, manage_metrics._TOTALS_DENOMINATOR_FIELD) == '6'

    def test_a_rendered_total_without_a_persisted_population_count_is_caught(self, plan_context):
        """D7(c): a total whose population count is missing from the store FAILS.

        Stated as its own test rather than folded into the round trip above,
        because this is the assertion the deliverable names: the guard must be
        the thing that fires when the count stops being persisted, not merely a
        by-product of a broader key sweep.
        """
        _drive_two_dispatched_phases('agg-marker-gate')
        cmd_generate(ns_generate('agg-marker-gate'))

        store = _store(plan_context, 'agg-marker-gate')
        rendered_cells = _total_row_cells(_report(plan_context, 'agg-marker-gate'))

        # Every rendered non-'-' Total cell must be able to state its coverage.
        for index, column in enumerate(_TOTAL_COLUMNS, start=1):
            if rendered_cells[index] == '-':
                continue
            count_field = (
                f'{manage_metrics._TOTALS_FIELDS[column]}'
                f'{manage_metrics._POPULATION_COUNT_SUFFIX}'
            )
            persisted = _top_level_field(store, count_field)
            assert persisted is not None, f'{column} rendered a total with no persisted population'
            assert int(persisted) > 0

    def test_spans_populations_marker_is_persisted(self, plan_context):
        """The cross-population Total marker exists as a field, not only as prose."""
        _drive_two_dispatched_phases('agg-spans')
        cmd_generate(ns_generate('agg-spans'))

        store = _store(plan_context, 'agg-spans')
        assert _top_level_field(store, manage_metrics._TOTALS_SPANS_POPULATIONS_FIELD) == 'false'

    def test_declared_exclusions_are_persisted_as_data(self, plan_context):
        """The exclusion semantics are a field, not a sentence in the render.

        They are the key to every boundary coverage shortfall the report shows;
        a script reading the store previously got the coverage numbers without
        the declaration that makes them interpretable.
        """
        _drive_two_dispatched_phases('agg-exclusions')
        cmd_generate(ns_generate('agg-exclusions'))

        store = _store(plan_context, 'agg-exclusions')
        persisted = _top_level_field(store, manage_metrics._BOUNDARY_EXCLUDED_CLASSES_FIELD)
        assert persisted is not None
        assert persisted.split(',') == list(manage_metrics.DISPATCH_BOUNDARY_EXCLUDED_CLASSES)

    def test_generate_result_echoes_every_total_with_its_population(self, plan_context):
        """The command's own return carries the triple too, derived from the map."""
        _drive_two_dispatched_phases('agg-echo')

        result = cmd_generate(ns_generate('agg-echo'))

        for field in manage_metrics._TOTALS_FIELDS.values():
            assert field in result
            assert f'{field}{manage_metrics._POPULATION_COUNT_SUFFIX}' in result
        assert result[manage_metrics._TOTALS_DENOMINATOR_FIELD] == 6

    def test_a_later_write_invalidates_the_aggregate_rather_than_stranding_it(self, plan_context):
        """The row-derived aggregate is present iff the most recent write computed it.

        Only `generate` computes the totals; every other writer moves the phase
        rows underneath them. Left in place they would silently stop summing the
        rows beside them — and this deliverable tells consumers to READ them
        instead of re-summing, so a stranded aggregate is a wrong answer given
        confidently. Presence is the freshness signal, deliberately rather than a
        timestamp comparison: `updated` and `totals_sampled_at` are both
        second-granularity, so a write in the same second would be invisible to
        one — as it is here, where the whole test runs inside one second.
        """
        plan_id = 'agg-stale'
        cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
        cmd_end_phase(ns_end_phase(plan_id, '4-plan', total_tokens=1000))
        cmd_generate(ns_generate(plan_id))
        store = _store(plan_context, plan_id)
        assert _top_level_field(store, 'totals_tokens') == '1000'
        assert _top_level_field(store, 'totals_sampled_at') is not None

        # A write that does NOT re-generate: the rows move.
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=999000))

        # Every row-derived key is gone — no stale value survives to be quoted.
        store = _store(plan_context, plan_id)
        for field in manage_metrics._TOTALS_FIELDS.values():
            assert _top_level_field(store, field) is None
            assert _top_level_field(store, f'{field}{manage_metrics._POPULATION_COUNT_SUFFIX}') is None
        assert _top_level_field(store, manage_metrics._TOTALS_DENOMINATOR_FIELD) is None
        assert _top_level_field(store, manage_metrics._TOTALS_SAMPLED_AT_FIELD) is None
        # `dispatch_boundary_excluded_classes` is deliberately NOT dropped: it derives
        # from a module constant rather than from the rows, so it cannot go stale
        # against them. Asserted so the scope of the invalidation is pinned, not
        # merely described.
        assert _top_level_field(store, manage_metrics._BOUNDARY_EXCLUDED_CLASSES_FIELD) is not None
        # The phase rows themselves are untouched by the invalidation.
        assert _phase_field(store, '5-execute', 'total_tokens') == '999000'

        # Re-generating restores it, now summing the moved rows.
        cmd_generate(ns_generate(plan_id))
        assert _top_level_field(_store(plan_context, plan_id), 'totals_tokens') == '1000000'

    def test_duration_totals_persist_milliseconds_not_rounded_seconds(self, plan_context):
        """The store keeps the operands' own precision.

        A decisecond-rounded seconds total puts the store BELOW the render's
        granularity: at 59.96 s the rounding flips `format_duration` from
        `60.0s` to `1m0s`, so the store and the report would disagree about the
        figure the store exists to make checkable.
        """
        plan_id = 'agg-ms-precision'
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        # Seeded rather than closed through `end-phase`: that path clamps the
        # worked value to the row's wall span, which is ~0 in a test that opens
        # and closes a phase in the same instant. The subject here is the
        # aggregate's UNIT, not the close path's clamp.
        raw = manage_metrics.read_metrics_raw(plan_id)
        raw['phases']['5-execute'].update(
            {'end_time': '2026-01-01T00:01:00Z', 'duration_seconds': 60.0,
             'agent_duration_ms': 59960, 'total_tokens': 10}
        )
        manage_metrics.write_metrics(plan_id, raw)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        assert _top_level_field(store, 'totals_worked_ms') == '59960'
        rendered = _total_row_cells(_report(plan_context, plan_id))[1]
        assert rendered.startswith('60.0s')


class TestWorkedTimeExcludesTheIdleGap:
    """The substrate the per-task ratio reads: worked effort, not operator idle.

    `plan-efficiency`'s `worked_seconds_per_task` is computed by an LLM from a
    reference contract, so the ratio itself has no script to test. What IS
    script-level, and what the deliverable actually rests on, is that the figure
    the contract tells it to read — `totals_worked_ms` — reflects worked time on
    a plan containing a long idle gap, while `totals_wall_ms` reflects the gap.
    If that separation did not hold, reading the worked field would change
    nothing and the fix would be cosmetic.
    """

    #: An overnight gap: the phase was open for eight hours.
    _WALL_MS = 8 * 60 * 60 * 1000
    #: The agent actually worked ten minutes of it.
    _WORKED_MS = 10 * 60 * 1000

    def _drive_phase_with_idle_gap(self, plan_id: str) -> None:
        """Open a phase eight hours ago and close it after ten minutes of work."""
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        raw = manage_metrics.read_metrics_raw(plan_id)
        opened = datetime.now(UTC) - timedelta(milliseconds=self._WALL_MS)
        raw['phases']['5-execute']['start_time'] = opened.isoformat()
        manage_metrics.write_metrics(plan_id, raw)
        cmd_end_phase(
            ns_end_phase(plan_id, '5-execute', total_tokens=5000, duration_ms=self._WORKED_MS)
        )

    def test_worked_excludes_the_gap_and_wall_includes_it(self, plan_context):
        """The two totals disagree by the idle gap — that IS the deliverable."""
        plan_id = 'idle-gap-split'
        self._drive_phase_with_idle_gap(plan_id)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        worked_ms = int(_top_level_field(store, 'totals_worked_ms'))
        wall_ms = int(_top_level_field(store, 'totals_wall_ms'))
        assert worked_ms == self._WORKED_MS
        # The wall span carries the whole gap (within a second of scheduling slack).
        assert wall_ms >= self._WALL_MS - 1000
        # A per-task figure over wall would grade ~48x more cost than was worked.
        assert wall_ms > worked_ms * 40

    def test_the_worked_figure_is_not_achieved_by_clamping(self, plan_context):
        """⛔ The plan forbids clamping, and no clamp fired here.

        `_clamp_worked_to_wall` only ever lowers a worked value TOWARD the wall
        span. On an idle-gap row worked is far below wall, so the clamp is a
        no-op and the recorded figure is the one the caller supplied — untouched,
        not reduced. Asserting the exact supplied value is what distinguishes
        "read the worked measurement" from "clamp the wall measurement".
        """
        plan_id = 'idle-gap-unclamped'
        self._drive_phase_with_idle_gap(plan_id)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        assert _phase_field(store, '5-execute', 'agent_duration_ms') == str(self._WORKED_MS)

        # Positive control through the SAME code path, not a direct call to the
        # clamp helper: a second plan closed with a worked value that EXCEEDS its
        # wall span comes back clamped. That establishes the clamp is wired into
        # `end-phase`, so the untouched value above is a property of the idle-gap
        # row rather than of a clamp that never runs.
        control = 'idle-gap-clamp-control'
        cmd_start_phase(ns_start_phase(control, '5-execute'))
        raw = manage_metrics.read_metrics_raw(control)
        opened = datetime.now(UTC) - timedelta(seconds=1)
        raw['phases']['5-execute']['start_time'] = opened.isoformat()
        manage_metrics.write_metrics(control, raw)
        cmd_end_phase(ns_end_phase(control, '5-execute', total_tokens=1, duration_ms=self._WALL_MS))

        clamped = int(_phase_field(_store(plan_context, control), '5-execute', 'agent_duration_ms'))
        assert clamped < self._WALL_MS

    def test_the_idle_residual_is_the_gap(self, plan_context):
        """Idle is published as its own figure, and it IS the operator's gap.

        Asserted against the fixture's own constants, not against
        `wall - worked` read back from the same store. That identity is how
        `idle_duration_ms` is computed, so asserting it pins neither operand and
        holds no matter what the operands become — an earlier version did exactly
        that and stayed green under a mutant that made worked equal wall
        (idle collapsed to 0, identity intact) while its sibling test failed.
        """
        plan_id = 'idle-gap-residual'
        self._drive_phase_with_idle_gap(plan_id)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        idle_ms = int(_top_level_field(store, 'totals_idle_ms'))
        expected_gap = self._WALL_MS - self._WORKED_MS
        # Within a second of scheduling slack on the seeded wall span.
        assert abs(idle_ms - expected_gap) <= 1000
        # And it is a large positive residual, not an incidental near-zero.
        assert idle_ms > self._WORKED_MS * 40
