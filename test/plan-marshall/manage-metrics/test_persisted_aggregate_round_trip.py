#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The rendered report and the store agree about what exists.

Three things `metrics.md` showed had no counterpart in `metrics.toon` at all:
the headline Total row, the population qualifier that makes it safe to quote,
and the caveats carrying the semantics (which measure won a reconciliation,
which dispatch classes are excluded by declaration). `write_metrics` ran BEFORE
the Total row was built, so the store's header carried no aggregate — a script
reading the record had to re-sum the rows itself and re-derive a population, and
could legitimately pick a different one than the renderer did.

These tests pin the round trip: every figure the Total row renders is locatable
in the store, beside the count of phase rows that fed it. A figure present only
in the render fails the deliverable.

They also pin the unclosed-boundary fold: a phase whose terminal close never
fired still has a dispatch-boundary file that accumulated a row per dispatch, and
that sum is folded into its Tokens cell as a LABELLED floor — while its duration
partiality verdict is deliberately left intact, because the boundary file cannot
honestly supply a wall-clock the close never stamped.
"""

import importlib.util
import re

import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_record_dispatch_boundary,
    ns_start_phase,
)

from conftest import get_script_path

_spec = importlib.util.spec_from_file_location(
    'manage_metrics_aggregate', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)

cmd_start_phase = manage_metrics.cmd_start_phase
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_generate = manage_metrics.cmd_generate
cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary

#: The Total row's six value columns, keyed as `_TOTALS_FIELDS` keys them. Read
#: from production so a column added there is covered here without an edit — a
#: hand-listed copy would reproduce the very drift these tests exist to catch.
_TOTAL_COLUMNS = tuple(manage_metrics._TOTALS_FIELDS)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Materialise the `status.json` sentinel every plan-scoped writer guards on."""
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        plan_dir = real_get_plan_dir(plan_id)
        plan_dir.mkdir(parents=True, exist_ok=True)
        sentinel = plan_dir / 'status.json'
        if not sentinel.is_file():
            sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


def _store(plan_context, plan_id: str) -> str:
    return (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text(encoding='utf-8')


def _report(plan_context, plan_id: str) -> str:
    return (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')


def _top_level_field(content: str, key: str) -> str | None:
    """Read a top-level `metrics.toon` key — the text above the first [phase]."""
    header = content.split('\n[', 1)[0]
    for line in header.splitlines():
        stripped = line.strip()
        if stripped.startswith(f'{key}:'):
            return stripped.split(':', 1)[1].strip()
    return None


def _phase_block(content: str, phase: str) -> str:
    start = content.index(f'[{phase}]')
    rest = content[start + len(f'[{phase}]'):]
    nxt = rest.find('\n[')
    return rest if nxt == -1 else rest[:nxt]


def _phase_field(content: str, phase: str, key: str) -> str | None:
    for line in _phase_block(content, phase).splitlines():
        stripped = line.strip()
        if stripped.startswith(f'{key}:'):
            return stripped.split(':', 1)[1].strip()
    return None


def _total_row_cells(report: str) -> list[str]:
    """Return the rendered Total row's cells, un-bolded and stripped."""
    for line in report.splitlines():
        if line.startswith('| **Total**'):
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            return [cell.strip('*').strip() for cell in cells]
    raise AssertionError('no Total row rendered')


def _drive_two_dispatched_phases(plan_id: str) -> None:
    """Close 4-plan and 5-execute with usage; leave the other four phases absent."""
    cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
    cmd_end_phase(ns_end_phase(plan_id, '4-plan', total_tokens=30000, tool_uses=12, duration_ms=45000))
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=70000, tool_uses=25, duration_ms=90000))


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


class TestInlineCostFieldOnEveryRow:
    """The inline-cost field is never absent — a figure, a zero, or a marker."""

    def test_unenriched_phase_carries_the_unmeasured_marker(self, plan_context):
        """No `enrich` stamp on the row means the phase was never measured."""
        _drive_two_dispatched_phases('inline-marker')
        cmd_generate(ns_generate('inline-marker'))

        store = _store(plan_context, 'inline-marker')
        assert _phase_field(store, '5-execute', 'inline_main_context_tokens') == 'unmeasured'

    def test_enriched_phase_with_no_inline_spend_carries_a_measured_zero(self, plan_context):
        """An `enrich`-stamped row with no inline spend is `0`, not the marker.

        The discriminator is the row's own `total_tokens_population` stamp, which
        `enrich` writes on every row it visits — so "measured, and it was zero"
        and "never measured" stay separable instead of both reading as absence.
        """
        plan_id = 'inline-measured-zero'
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=5000))
        # Stamp the row the way enrich's dispatched branch does, with no inline sum.
        raw = manage_metrics.read_metrics_raw(plan_id)
        raw['phases']['5-execute']['total_tokens_population'] = manage_metrics.POPULATION_DISPATCHED
        manage_metrics.write_metrics(plan_id, raw)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        assert _phase_field(store, '5-execute', 'inline_main_context_tokens') == '0'

    def test_a_stale_marker_is_re_derived_rather_than_preserved(self, plan_context):
        """A later `enrich` is not shadowed by an earlier generate's marker."""
        plan_id = 'inline-restale'
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=5000))
        cmd_generate(ns_generate(plan_id))
        assert _phase_field(_store(plan_context, plan_id), '5-execute',
                            'inline_main_context_tokens') == 'unmeasured'

        # enrich now visits the phase and measures no inline spend.
        raw = manage_metrics.read_metrics_raw(plan_id)
        raw['phases']['5-execute']['total_tokens_population'] = manage_metrics.POPULATION_DISPATCHED
        manage_metrics.write_metrics(plan_id, raw)
        cmd_generate(ns_generate(plan_id))

        assert _phase_field(_store(plan_context, plan_id), '5-execute',
                            'inline_main_context_tokens') == '0'


class TestUnclosedBoundaryFold:
    """A never-closed phase's recorded dispatch spend is folded in, labelled."""

    @staticmethod
    def _drive_unclosed_finalize(plan_id: str) -> None:
        """5-execute closes normally; 6-finalize dispatches twice and never closes."""
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=20000, tool_uses=8, duration_ms=30000))
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=500000)
        )
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=700000)
        )

    def test_boundary_sum_is_folded_into_the_cell(self, plan_context):
        """The phase renders its recorded spend instead of `-`."""
        self._drive_unclosed_finalize('unclosed-fold')
        cmd_generate(ns_generate('unclosed-fold'))

        report = _report(plan_context, 'unclosed-fold')
        finalize_row = next(line for line in report.splitlines() if line.startswith('| 6-finalize'))
        assert '1,200,000' in finalize_row

    def test_the_folded_cell_is_labelled(self, plan_context):
        """A floor is marked as one — an unmarked cell would assert a total."""
        self._drive_unclosed_finalize('unclosed-label')
        cmd_generate(ns_generate('unclosed-label'))

        report = _report(plan_context, 'unclosed-label')
        finalize_row = next(line for line in report.splitlines() if line.startswith('| 6-finalize'))
        assert '(boundary floor)' in finalize_row
        assert 'Marked `(boundary floor)`' in report

    def test_the_fold_reaches_the_total_and_its_population_count(self, plan_context):
        """The folded figure is a phase that counts, not a footnote."""
        self._drive_unclosed_finalize('unclosed-total')
        cmd_generate(ns_generate('unclosed-total'))

        store = _store(plan_context, 'unclosed-total')
        assert _top_level_field(store, 'totals_tokens') == '1220000'
        assert _top_level_field(store, 'totals_tokens_population_count') == '2'

    def test_the_cell_source_is_persisted(self, plan_context):
        """Provenance is a field, so a consumer need not re-run the comparison."""
        self._drive_unclosed_finalize('unclosed-source')
        cmd_generate(ns_generate('unclosed-source'))

        store = _store(plan_context, 'unclosed-source')
        assert _phase_field(store, '6-finalize', 'tokens_cell_source') == 'unclosed_boundary_floor'
        assert _phase_field(store, '5-execute', 'tokens_cell_source') == 'total_tokens'

    def test_the_duration_partiality_verdict_survives_the_fold(self, plan_context):
        """⛔ The token fold must NOT launder the phase into looking closed.

        The boundary file records per-dispatch spans and cannot honestly supply a
        phase wall-clock the close never stamped, so the phase stays listed as
        missing its end_time marker and renders no duration.
        """
        self._drive_unclosed_finalize('unclosed-partial')

        result = cmd_generate(ns_generate('unclosed-partial'))

        assert result['any_phase_missing_end_time'] is True
        assert '6-finalize' in result['phases_missing_end_time']
        report = _report(plan_context, 'unclosed-partial')
        assert 'Phases missing an end_time boundary marker' in report
        finalize_row = next(line for line in report.splitlines() if line.startswith('| 6-finalize'))
        # Worked / Reported (wall) / Idle all render absent for the unclosed row.
        cells = [cell.strip() for cell in finalize_row.strip().strip('|').split('|')]
        assert cells[1] == '-'
        assert cells[2] == '-'

    def test_a_closed_phase_takes_no_floor_marker(self, plan_context):
        """The negative control: `end_time` alone is what withholds the marker.

        The recorded total is set BELOW the boundary sum on purpose, so the
        boundary sum still wins the reconciliation and still feeds the cell. The
        only difference from the unclosed case is the `end_time` marker — which
        makes this a real control over the guard. Closing with a LARGER total
        would pass whether or not the guard existed, since the cell would then be
        fed by `total_tokens` and could never be marked a floor.
        """
        self._drive_unclosed_finalize('unclosed-control')
        cmd_end_phase(ns_end_phase('unclosed-control', '6-finalize', total_tokens=100000))

        cmd_generate(ns_generate('unclosed-control'))

        store = _store(plan_context, 'unclosed-control')
        # Precondition: the cell IS the boundary sum, so only the close withholds
        # the marker.
        assert _phase_field(store, '6-finalize', 'tokens_cell_source') == 'dispatch_boundary_total'
        assert _phase_field(store, '6-finalize', 'end_time') is not None
        assert '(boundary floor)' not in _report(plan_context, 'unclosed-control')

    def test_the_fold_never_lowers_a_cell(self, plan_context):
        """A boundary sum below the recorded figure does not replace it."""
        plan_id = 'unclosed-no-lower'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=1000)
        )
        # A recorded total the reconciliation already trusts, on the same unclosed row.
        raw = manage_metrics.read_metrics_raw(plan_id)
        raw['phases']['6-finalize']['total_tokens'] = 900000
        manage_metrics.write_metrics(plan_id, raw)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        assert _top_level_field(store, 'totals_tokens') == '900000'
        assert _phase_field(store, '6-finalize', 'tokens_cell_source') == 'total_tokens'


def test_four_field_persistence_walks_the_canonical_label_set():
    """The persist loop's population IS the render's, not a second copy.

    A hardcoded field list cannot drift visibly: a fifth field added to
    `_FOUR_FIELD_USAGE_LABELS` would gain a render bullet and a contract test
    while never being persisted, and the render's presence guard would read the
    omission as an absent measurement rather than as a persister that never
    looked.
    """
    assert manage_metrics._FOUR_FIELD_USAGE_FIELDS == tuple(
        field for field, _label in manage_metrics._FOUR_FIELD_USAGE_LABELS
    )
    source = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py').read_text(
        encoding='utf-8'
    )
    enrich_body = source.split('def cmd_enrich(', 1)[1]
    # The literal tuple this loop used to spell out must not have come back.
    assert not re.search(r"for field in \(\s*'input_tokens'", enrich_body)
    assert 'for field in _FOUR_FIELD_USAGE_FIELDS:' in enrich_body
