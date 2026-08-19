#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The rendered report and the store agree about what exists."""


import re

import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_generate,
    ns_record_dispatch_boundary,
    ns_start_phase,
)
from _persisted_aggregate_round_trip_fixtures import (
    _drive_two_dispatched_phases,
    _phase_field,
    _report,
    _store,
    _top_level_field,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_generate,
    cmd_record_dispatch_boundary,
    cmd_start_phase,
    manage_metrics,
)

from conftest import get_script_path


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

        The phase stays listed as missing its `end_time` marker, and no
        wall-clock duration is derived from the boundary file — which records
        per-dispatch spans, not the phase span the close never stamped.

        The fixture gives the phase an ACCUMULATOR as well as boundary rows, so
        the Worked cell is populated by a route the fold does not control. That
        is the point: an earlier version of this test used a boundary-only
        fixture, where Worked rendered `-` because nothing had ever been
        recorded rather than because the fold withheld it — it asserted the
        right cells for the wrong reason and could not fail against the defect
        it names. Here the row demonstrably CAN render a duration, and the
        assertion is that the fold still does not supply the wall-clock one.
        """
        plan_id = 'unclosed-partial'
        self._drive_unclosed_finalize(plan_id)
        cmd_accumulate_agent_usage(
            ns_accumulate(plan_id, '6-finalize', total_tokens=1000, duration_ms=600000)
        )

        result = cmd_generate(ns_generate(plan_id))

        assert result['any_phase_missing_end_time'] is True
        assert '6-finalize' in result['phases_missing_end_time']
        report = _report(plan_context, plan_id)
        assert 'Phases missing an end_time boundary marker' in report
        finalize_row = next(line for line in report.splitlines() if line.startswith('| 6-finalize'))
        cells = [cell.strip() for cell in finalize_row.strip().strip('|').split('|')]
        # Precondition — the accumulator route DID populate Worked, so a `-` in
        # the wall column below cannot be "nothing was ever recorded".
        assert cells[1] == '10m0s'
        # The fold supplies no wall-clock span, and no idle residual derived from one.
        assert cells[2] == '-'
        assert cells[3] == '-'
        # And the token cell is still the labelled floor, so the fold did fire.
        assert '(boundary floor)' in cells[4]

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
        # Scoped to the DATA ROWS: the end_time-presence annotation names the
        # marker in prose to explain it, which is not a cell carrying it.
        report = _report(plan_context, 'unclosed-control')
        data_rows = [line for line in report.splitlines() if line.startswith('| ')]
        assert not any('(boundary floor)' in row for row in data_rows)

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


class TestOverCoveringBoundaryIsNotCalledAFloor:
    """A sum the module classifies as `over` is folded, but never labelled a floor.

    `_boundary_coverage_state` calls `over` — more recorded boundary rows than
    sampled dispatches — impossible for a single population and potentially
    double-counted across a resume, and `_eligible_dispatched_measures` refuses
    it the reconciliation maximum for exactly that reason. The unclosed-phase
    fold bypasses eligibility on purpose (the alternative is rendering nothing
    for a phase that demonstrably spent something), so the marker is what has to
    stay honest: `floor` asserts a lower bound the classification denies.
    """

    @staticmethod
    def _drive_over_covering_unclosed(plan_id: str) -> None:
        """An unclosed phase with 3 boundary rows but only 1 sampled dispatch."""
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        for tokens in (300000, 300000, 300000):
            cmd_record_dispatch_boundary(
                ns_record_dispatch_boundary(plan_id, '5-execute', 'step_complete', total_tokens=tokens)
            )
        raw = manage_metrics.read_metrics_raw(plan_id)
        raw['phases']['5-execute']['total_tokens'] = 10000
        raw['phases']['5-execute']['subagent_samples'] = 1
        manage_metrics.write_metrics(plan_id, raw)

    def test_the_coverage_state_is_over(self, plan_context):
        """Precondition — without it the rest of this class proves nothing.

        Read AFTER `generate`, because `dispatch_boundary_rows_recorded` — the
        numerator `_boundary_coverage_state` compares — is written by `generate`
        from the boundary file, not by the boundary writer itself.
        """
        plan_id = 'over-precondition'
        self._drive_over_covering_unclosed(plan_id)
        cmd_generate(ns_generate(plan_id))

        raw = manage_metrics.read_metrics_raw(plan_id)
        assert manage_metrics._boundary_coverage_state(raw['phases']['5-execute']) == 'over'

    def test_the_cell_is_not_marked_a_floor(self, plan_context):
        """The lower-bound label is withheld from a figure that may double-count."""
        plan_id = 'over-not-floor'
        self._drive_over_covering_unclosed(plan_id)

        cmd_generate(ns_generate(plan_id))

        report = _report(plan_context, plan_id)
        row = next(line for line in report.splitlines() if line.startswith('| 5-execute'))
        assert '900,000' in row
        assert '(boundary floor)' not in row
        assert '(boundary sum, over-covering)' in row

    def test_the_marker_carries_its_own_key(self, plan_context):
        """A marker without a key is one the reader cannot interpret."""
        plan_id = 'over-key'
        self._drive_over_covering_unclosed(plan_id)

        cmd_generate(ns_generate(plan_id))

        report = _report(plan_context, plan_id)
        assert 'Marked `(boundary sum, over-covering)`' in report
        assert 'not** labelled a floor' in report
        # The key states the figure is bounded in NEITHER direction. Asserted
        # because an earlier wording claimed an upper bound, which the declared
        # exclusions below the table deny — the file omits every dispatch class
        # that registers no boundary.
        assert 'bounded in neither direction' in report

    def test_the_provenance_is_persisted_distinctly(self, plan_context):
        """The store separates the two cases, not only the rendered text."""
        plan_id = 'over-provenance'
        self._drive_over_covering_unclosed(plan_id)

        cmd_generate(ns_generate(plan_id))

        store = _store(plan_context, plan_id)
        assert _phase_field(store, '5-execute', 'tokens_cell_source') == 'unclosed_boundary_over_covering'

    def test_a_partial_coverage_row_still_gets_the_floor_marker(self, plan_context):
        """The negative control: `floor` is withheld only from `over`.

        Same shape, but with more sampled dispatches than recorded rows — a
        genuine under-count, where a lower bound IS what the figure is.
        """
        plan_id = 'over-control-partial'
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '5-execute', 'step_complete', total_tokens=900000)
        )
        raw = manage_metrics.read_metrics_raw(plan_id)
        raw['phases']['5-execute']['total_tokens'] = 10000
        raw['phases']['5-execute']['subagent_samples'] = 5
        manage_metrics.write_metrics(plan_id, raw)

        cmd_generate(ns_generate(plan_id))

        # Precondition, read after generate: this row's coverage is `partial`,
        # so the ONLY difference from the over-covering case is the classification.
        assert manage_metrics._boundary_coverage_state(
            manage_metrics.read_metrics_raw(plan_id)['phases']['5-execute']
        ) == 'partial'
        report = _report(plan_context, plan_id)
        row = next(line for line in report.splitlines() if line.startswith('| 5-execute'))
        assert '(boundary floor)' in row
        assert 'over-covering' not in row
